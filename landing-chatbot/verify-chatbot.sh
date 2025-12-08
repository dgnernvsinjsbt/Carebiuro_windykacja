#!/bin/bash

# Verification script for AI Chatbot System
# Run this to verify all components are working

echo "🤖 AI Chatbot System - Verification"
echo "===================================="
echo ""

# Check if OpenAI package is installed
echo "1. Checking OpenAI package..."
if npm list openai &> /dev/null; then
    echo "   ✅ OpenAI package installed"
else
    echo "   ❌ OpenAI package NOT installed"
    echo "   Run: npm install openai"
    exit 1
fi

# Check if FAQ file exists
echo ""
echo "2. Checking FAQ knowledge base..."
if [ -f "public/faq.json" ]; then
    FAQ_COUNT=$(jq '. | length' public/faq.json 2>/dev/null)
    if [ $? -eq 0 ]; then
        echo "   ✅ FAQ file exists ($FAQ_COUNT entries)"
    else
        echo "   ⚠️  FAQ file exists but invalid JSON"
    fi
else
    echo "   ❌ FAQ file NOT found"
    exit 1
fi

# Check if widget.js exists
echo ""
echo "3. Checking widget.js..."
if [ -f "public/widget.js" ]; then
    WIDGET_SIZE=$(wc -c < public/widget.js)
    echo "   ✅ Widget file exists (${WIDGET_SIZE} bytes)"
else
    echo "   ❌ Widget file NOT found"
    exit 1
fi

# Check if API endpoints exist
echo ""
echo "4. Checking API endpoints..."
if [ -f "app/api/chat/route.ts" ]; then
    echo "   ✅ Chat API endpoint exists"
else
    echo "   ❌ Chat API endpoint NOT found"
    exit 1
fi

if [ -f "app/api/widget.js/route.ts" ]; then
    echo "   ✅ Widget.js API endpoint exists"
else
    echo "   ❌ Widget.js API endpoint NOT found"
    exit 1
fi

# Check if lib files exist
echo ""
echo "5. Checking library files..."
if [ -f "lib/faq-matcher.ts" ]; then
    echo "   ✅ FAQ matcher exists"
else
    echo "   ❌ FAQ matcher NOT found"
    exit 1
fi

if [ -f "lib/openai.ts" ]; then
    echo "   ✅ OpenAI client exists"
else
    echo "   ❌ OpenAI client NOT found"
    exit 1
fi

# Check if .env.local exists
echo ""
echo "6. Checking environment configuration..."
if [ -f ".env.local" ]; then
    if grep -q "OPENAI_API_KEY" .env.local; then
        KEY_VALUE=$(grep "OPENAI_API_KEY" .env.local | cut -d'=' -f2)
        if [ -z "$KEY_VALUE" ] || [ "$KEY_VALUE" = "sk-your-api-key-here" ]; then
            echo "   ⚠️  .env.local exists but OPENAI_API_KEY not configured"
            echo "   Add your OpenAI key to .env.local"
        else
            echo "   ✅ OPENAI_API_KEY configured"
        fi
    else
        echo "   ⚠️  .env.local exists but missing OPENAI_API_KEY"
    fi
else
    echo "   ⚠️  .env.local NOT found (copy from .env.example)"
fi

# Check if test file exists
echo ""
echo "7. Checking test files..."
if [ -f "test-embed.html" ]; then
    echo "   ✅ Test embed file exists"
else
    echo "   ⚠️  Test embed file NOT found"
fi

echo ""
echo "===================================="
echo "✅ All core files verified!"
echo ""
echo "Next steps:"
echo "1. Configure OPENAI_API_KEY in .env.local"
echo "2. Run: npm run dev"
echo "3. Open: http://localhost:3001"
echo "4. Click 💬 button to test chatbot"
echo ""
echo "For embed test:"
echo "- Open test-embed.html in browser"
echo ""
echo "See CHATBOT_SETUP.md for detailed documentation"
echo ""
