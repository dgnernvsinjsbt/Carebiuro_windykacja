#!/usr/bin/env python3
"""
MOODENG RSI Momentum - Master Optimization Framework
Systematically tests all optimization categories to find robust BingX-adapted parameters
"""

import pandas as pd
import numpy as np
from datetime import datetime, time
import itertools
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')

class MOODENGMasterOptimizer:
    """Master optimizer following the 6-step framework"""

    def __init__(self, data_path: str):
        """Initialize with BingX data"""
        print("Loading MOODENG BingX data...")
        self.df = pd.read_csv(data_path)
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])
        self.df = self.df.sort_values('timestamp').reset_index(drop=True)

        # Calculate base indicators
        self._calculate_indicators()
        print(f"✅ Loaded {len(self.df):,} candles from {self.df['timestamp'].min()} to {self.df['timestamp'].max()}")

    def _calculate_indicators(self):
        """Calculate all technical indicators"""
        # RSI
        delta = self.df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        self.df['rsi'] = 100 - (100 / (1 + rs))

        # SMA
        self.df['sma20'] = self.df['close'].rolling(window=20).mean()
        self.df['sma50'] = self.df['close'].rolling(window=50).mean()

        # ATR
        high_low = self.df['high'] - self.df['low']
        high_close = abs(self.df['high'] - self.df['close'].shift())
        low_close = abs(self.df['low'] - self.df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        self.df['atr'] = tr.rolling(window=14).mean()

        # Body size
        self.df['body_pct'] = abs(self.df['close'] - self.df['open']) / self.df['open'] * 100

        # Session labels
        self.df['hour'] = self.df['timestamp'].dt.hour
        self.df['session'] = self.df['hour'].apply(self._get_session)

    def _get_session(self, hour):
        """Map hour to trading session"""
        if 0 <= hour < 8:
            return 'asia'
        elif 8 <= hour < 14:
            return 'europe'
        elif 14 <= hour < 21:
            return 'us'
        else:  # 21-24
            return 'overnight'

    def backtest(self, config: Dict) -> Dict:
        """
        Run backtest with given configuration

        config = {
            'rsi_threshold': 55,
            'body_min': 0.5,
            'sl_atr_mult': 1.0,
            'tp_atr_mult': 4.0,
            'max_hold_bars': 60,
            'sessions': ['all'] or ['us', 'europe'],
            'htf_filter': None or {'type': 'sma_trend', '5m_above_sma50': True},
            'entry_type': 'market' or 'limit',
            'limit_pullback_pct': 0.2,
            'volume_filter': None or {'min_mult': 1.5},
            'volatility_filter': None or {'min_atr_pct': 0.3, 'max_atr_pct': 2.0}
        }
        """
        df = self.df.copy()

        # Filter sessions
        if config.get('sessions') and config['sessions'] != ['all']:
            df = df[df['session'].isin(config['sessions'])].copy()

        trades = []
        in_position = False
        entry_idx = None
        entry_price = None
        stop_loss = None
        take_profit = None
        direction = 'long'  # MOODENG is long-only

        for i in range(100, len(df)):  # Start after indicators warm up
            if in_position:
                # Check exits
                bars_held = i - entry_idx
                exit_reason = None
                exit_price = None

                # Time exit
                if bars_held >= config.get('max_hold_bars', 60):
                    exit_reason = 'timeout'
                    exit_price = df.iloc[i]['close']

                # Stop loss (check low of bar)
                elif df.iloc[i]['low'] <= stop_loss:
                    exit_reason = 'sl'
                    exit_price = stop_loss

                # Take profit (check high of bar)
                elif df.iloc[i]['high'] >= take_profit:
                    exit_reason = 'tp'
                    exit_price = take_profit

                if exit_reason:
                    # Calculate PnL
                    pnl_pct = ((exit_price - entry_price) / entry_price) * 100
                    pnl_pct -= 0.10  # BingX taker fees: 0.05% x 2

                    trades.append({
                        'entry_time': df.iloc[entry_idx]['timestamp'],
                        'exit_time': df.iloc[i]['timestamp'],
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'exit_reason': exit_reason,
                        'pnl_pct': pnl_pct,
                        'bars_held': bars_held
                    })

                    in_position = False
                    entry_idx = None
                    entry_price = None
                    stop_loss = None
                    take_profit = None

            else:
                # Check entry signals
                current = df.iloc[i]
                prev = df.iloc[i-1]

                # Original MOODENG RSI entry signal
                rsi_cross = prev['rsi'] < config.get('rsi_threshold', 55) and current['rsi'] >= config.get('rsi_threshold', 55)
                bullish_candle = current['body_pct'] >= config.get('body_min', 0.5) and current['close'] > current['open']
                above_sma = current['close'] > current['sma20']

                if not (rsi_cross and bullish_candle and above_sma):
                    continue

                # Apply HTF filter if configured
                if config.get('htf_filter'):
                    if not self._check_htf_filter(df, i, config['htf_filter']):
                        continue

                # Apply volume filter if configured
                if config.get('volume_filter'):
                    avg_volume = df['volume'].iloc[i-20:i].mean()
                    if current['volume'] < avg_volume * config['volume_filter']['min_mult']:
                        continue

                # Apply volatility filter if configured
                if config.get('volatility_filter'):
                    atr_pct = (current['atr'] / current['close']) * 100
                    vf = config['volatility_filter']
                    if atr_pct < vf.get('min_atr_pct', 0) or atr_pct > vf.get('max_atr_pct', 999):
                        continue

                # Determine entry price
                if config.get('entry_type') == 'limit':
                    # Limit order pullback entry
                    pullback = config.get('limit_pullback_pct', 0.2) / 100
                    entry_price = current['close'] * (1 - pullback)

                    # Check if next bar fills the limit (conservative: needs to touch our price)
                    if i+1 < len(df):
                        next_bar = df.iloc[i+1]
                        if next_bar['low'] <= entry_price:
                            # Filled
                            pass
                        else:
                            # Not filled, skip trade
                            continue
                    else:
                        continue
                else:
                    # Market order
                    entry_price = current['close']

                # Set exits
                sl_atr_mult = config.get('sl_atr_mult', 1.0)
                tp_atr_mult = config.get('tp_atr_mult', 4.0)

                stop_loss = entry_price - (current['atr'] * sl_atr_mult)
                take_profit = entry_price + (current['atr'] * tp_atr_mult)

                in_position = True
                entry_idx = i

        # Calculate metrics
        if len(trades) == 0:
            return {
                'trades': 0,
                'win_rate': 0,
                'gross_return': 0,
                'net_return': 0,
                'max_dd': 0,
                'ratio': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'profit_factor': 0,
                'expectancy': 0
            }

        trades_df = pd.DataFrame(trades)

        # Win rate
        wins = trades_df[trades_df['pnl_pct'] > 0]
        losses = trades_df[trades_df['pnl_pct'] < 0]
        win_rate = len(wins) / len(trades_df) * 100

        # Returns
        trades_df['cumulative'] = (1 + trades_df['pnl_pct']/100).cumprod()
        net_return = (trades_df['cumulative'].iloc[-1] - 1) * 100

        # Max drawdown
        cumulative = trades_df['cumulative']
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max * 100
        max_dd = abs(drawdown.min())

        # Profit metrics
        avg_win = wins['pnl_pct'].mean() if len(wins) > 0 else 0
        avg_loss = abs(losses['pnl_pct'].mean()) if len(losses) > 0 else 0
        profit_factor = wins['pnl_pct'].sum() / abs(losses['pnl_pct'].sum()) if len(losses) > 0 else 999
        expectancy = trades_df['pnl_pct'].mean()

        # Return/DD ratio
        ratio = net_return / max_dd if max_dd > 0 else 0

        return {
            'trades': len(trades_df),
            'win_rate': win_rate,
            'net_return': net_return,
            'max_dd': max_dd,
            'ratio': ratio,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'expectancy': expectancy,
            'trades_df': trades_df
        }

    def _check_htf_filter(self, df, idx, htf_config):
        """Check higher timeframe filter"""
        # For now, skip HTF - would need 5m/15m/1H data
        # This is placeholder for future enhancement
        return True

    def optimize_sessions(self):
        """Step 2: Find best trading sessions"""
        print("\n" + "="*80)
        print("STEP 2: SESSION-BASED OPTIMIZATION")
        print("="*80)

        sessions = ['all', 'asia', 'europe', 'us', 'overnight']
        results = []

        base_config = {
            'rsi_threshold': 55,
            'body_min': 0.5,
            'sl_atr_mult': 1.0,
            'tp_atr_mult': 4.0,
            'max_hold_bars': 60,
            'entry_type': 'market'
        }

        for session in sessions:
            config = base_config.copy()
            config['sessions'] = [session] if session != 'all' else ['all']

            metrics = self.backtest(config)
            results.append({
                'session': session,
                **metrics
            })

            print(f"\n{session.upper()}")
            print(f"  Trades: {metrics['trades']}")
            print(f"  Win Rate: {metrics['win_rate']:.1f}%")
            print(f"  Return: {metrics['net_return']:.2f}%")
            print(f"  Max DD: {metrics['max_dd']:.2f}%")
            print(f"  Ratio: {metrics['ratio']:.2f}x")

        results_df = pd.DataFrame(results)
        results_df = results_df.sort_values('ratio', ascending=False)

        print(f"\n🏆 BEST SESSION: {results_df.iloc[0]['session'].upper()}")
        print(f"   Ratio: {results_df.iloc[0]['ratio']:.2f}x")

        return results_df

    def optimize_sl_tp(self, best_sessions=['all']):
        """Step 3: Optimize stop loss and take profit"""
        print("\n" + "="*80)
        print("STEP 3: DYNAMIC SL/TP OPTIMIZATION")
        print("="*80)

        sl_values = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
        tp_values = [2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0]

        results = []

        for sl, tp in itertools.product(sl_values, tp_values):
            config = {
                'rsi_threshold': 55,
                'body_min': 0.5,
                'sl_atr_mult': sl,
                'tp_atr_mult': tp,
                'max_hold_bars': 60,
                'sessions': best_sessions,
                'entry_type': 'market'
            }

            metrics = self.backtest(config)

            if metrics['trades'] >= 30:  # Minimum statistical significance
                results.append({
                    'sl_mult': sl,
                    'tp_mult': tp,
                    'rr_ratio': tp/sl,
                    **metrics
                })

        results_df = pd.DataFrame(results)
        results_df = results_df.sort_values('ratio', ascending=False)

        print(f"\n📊 Tested {len(results_df)} SL/TP combinations")
        print(f"\nTop 10 configurations:")
        print(results_df[['sl_mult', 'tp_mult', 'trades', 'win_rate', 'net_return', 'max_dd', 'ratio']].head(10).to_string(index=False))

        print(f"\n🏆 BEST SL/TP: SL={results_df.iloc[0]['sl_mult']}x ATR, TP={results_df.iloc[0]['tp_mult']}x ATR")
        print(f"   Ratio: {results_df.iloc[0]['ratio']:.2f}x")
        print(f"   Win Rate: {results_df.iloc[0]['win_rate']:.1f}%")
        print(f"   Return: {results_df.iloc[0]['net_return']:.2f}%")

        return results_df

    def optimize_entry_type(self, best_config):
        """Step 5: Test limit order entries"""
        print("\n" + "="*80)
        print("STEP 5: ENTRY TYPE OPTIMIZATION")
        print("="*80)

        pullback_values = [0.0, 0.1, 0.2, 0.3, 0.5]
        results = []

        for pullback in pullback_values:
            config = best_config.copy()
            config['entry_type'] = 'limit' if pullback > 0 else 'market'
            config['limit_pullback_pct'] = pullback

            metrics = self.backtest(config)

            results.append({
                'entry_type': 'market' if pullback == 0 else f'limit -{pullback}%',
                'pullback_pct': pullback,
                **metrics
            })

            print(f"\n{results[-1]['entry_type']}")
            print(f"  Trades: {metrics['trades']}")
            print(f"  Win Rate: {metrics['win_rate']:.1f}%")
            print(f"  Return: {metrics['net_return']:.2f}%")
            print(f"  Ratio: {metrics['ratio']:.2f}x")

        results_df = pd.DataFrame(results)
        results_df = results_df.sort_values('ratio', ascending=False)

        print(f"\n🏆 BEST ENTRY: {results_df.iloc[0]['entry_type']}")
        print(f"   Ratio: {results_df.iloc[0]['ratio']:.2f}x")

        return results_df

    def optimize_filters(self, best_config):
        """Step 6: Test additional filters"""
        print("\n" + "="*80)
        print("STEP 6: ADDITIONAL FILTERS OPTIMIZATION")
        print("="*80)

        results = []

        # Baseline (no filters)
        baseline = self.backtest(best_config)
        results.append({
            'filter_type': 'baseline',
            **baseline
        })
        print(f"\nBASELINE (no filters)")
        print(f"  Trades: {baseline['trades']}")
        print(f"  Win Rate: {baseline['win_rate']:.1f}%")
        print(f"  Return: {baseline['net_return']:.2f}%")
        print(f"  Ratio: {baseline['ratio']:.2f}x")

        # Volume filter
        volume_mults = [1.2, 1.5, 2.0]
        for mult in volume_mults:
            config = best_config.copy()
            config['volume_filter'] = {'min_mult': mult}

            metrics = self.backtest(config)
            results.append({
                'filter_type': f'volume >{mult}x avg',
                **metrics
            })

            print(f"\nVOLUME FILTER (>{mult}x average)")
            print(f"  Trades: {metrics['trades']}")
            print(f"  Win Rate: {metrics['win_rate']:.1f}%")
            print(f"  Return: {metrics['net_return']:.2f}%")
            print(f"  Ratio: {metrics['ratio']:.2f}x")

        results_df = pd.DataFrame(results)
        results_df = results_df.sort_values('ratio', ascending=False)

        print(f"\n🏆 BEST FILTER: {results_df.iloc[0]['filter_type']}")
        print(f"   Ratio: {results_df.iloc[0]['ratio']:.2f}x")

        return results_df

    def run_full_optimization(self):
        """Run complete optimization pipeline"""
        print("\n" + "="*80)
        print("MOODENG MASTER OPTIMIZATION FRAMEWORK")
        print("="*80)

        # Step 2: Sessions
        session_results = self.optimize_sessions()
        best_session = session_results.iloc[0]['session']
        best_sessions = [best_session] if best_session != 'all' else ['all']

        # Step 3: SL/TP
        sltp_results = self.optimize_sl_tp(best_sessions)
        best_sl = sltp_results.iloc[0]['sl_mult']
        best_tp = sltp_results.iloc[0]['tp_mult']

        best_config = {
            'rsi_threshold': 55,
            'body_min': 0.5,
            'sl_atr_mult': best_sl,
            'tp_atr_mult': best_tp,
            'max_hold_bars': 60,
            'sessions': best_sessions,
            'entry_type': 'market'
        }

        # Step 5: Entry type
        entry_results = self.optimize_entry_type(best_config)
        if entry_results.iloc[0]['pullback_pct'] > 0:
            best_config['entry_type'] = 'limit'
            best_config['limit_pullback_pct'] = entry_results.iloc[0]['pullback_pct']

        # Step 6: Filters
        filter_results = self.optimize_filters(best_config)

        # Final configuration
        print("\n" + "="*80)
        print("FINAL OPTIMIZED CONFIGURATION")
        print("="*80)

        final_metrics = self.backtest(best_config)

        print(f"\nConfiguration:")
        print(f"  RSI Threshold: {best_config['rsi_threshold']}")
        print(f"  Min Body: {best_config['body_min']}%")
        print(f"  Stop Loss: {best_config['sl_atr_mult']}x ATR")
        print(f"  Take Profit: {best_config['tp_atr_mult']}x ATR")
        print(f"  Max Hold: {best_config['max_hold_bars']} bars")
        print(f"  Sessions: {best_config['sessions']}")
        print(f"  Entry Type: {best_config['entry_type']}")

        print(f"\nPerformance:")
        print(f"  Trades: {final_metrics['trades']}")
        print(f"  Win Rate: {final_metrics['win_rate']:.1f}%")
        print(f"  Net Return: {final_metrics['net_return']:.2f}%")
        print(f"  Max DD: {final_metrics['max_dd']:.2f}%")
        print(f"  Return/DD Ratio: {final_metrics['ratio']:.2f}x")
        print(f"  Profit Factor: {final_metrics['profit_factor']:.2f}")
        print(f"  Expectancy: {final_metrics['expectancy']:.3f}%")

        # Save results
        results = {
            'config': best_config,
            'metrics': final_metrics,
            'session_results': session_results,
            'sltp_results': sltp_results,
            'entry_results': entry_results,
            'filter_results': filter_results
        }

        return results

if __name__ == '__main__':
    optimizer = MOODENGMasterOptimizer('./trading/moodeng_30d_bingx.csv')
    results = optimizer.run_full_optimization()

    # Save detailed trades
    if 'trades_df' in results['metrics']:
        results['metrics']['trades_df'].to_csv('./trading/results/MOODENG_optimized_trades.csv', index=False)
        print(f"\n✅ Saved detailed trades to ./trading/results/MOODENG_optimized_trades.csv")
