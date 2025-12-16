-- Nova-Style E-commerce Schema
-- Products, variants (sizes), and inventory management

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Categories enum
CREATE TYPE product_category AS ENUM ('women', 'men');

-- Products table
CREATE TABLE products (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL,
  slug TEXT UNIQUE NOT NULL,
  category product_category NOT NULL,
  color TEXT NOT NULL,
  price INTEGER NOT NULL, -- Price in grosze (PLN * 100)
  image_url TEXT,
  description TEXT,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Product variants (sizes with inventory)
CREATE TABLE product_variants (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  product_id UUID REFERENCES products(id) ON DELETE CASCADE,
  size TEXT NOT NULL, -- XS, S, M, L, XL, XXL
  stock INTEGER DEFAULT 0,
  sku TEXT UNIQUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(product_id, size)
);

-- Admin users for login
CREATE TABLE admin_users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  name TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Orders table (basic)
CREATE TABLE orders (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  customer_email TEXT NOT NULL,
  customer_name TEXT NOT NULL,
  customer_phone TEXT,
  shipping_address TEXT NOT NULL,
  total_amount INTEGER NOT NULL, -- in grosze
  status TEXT DEFAULT 'pending', -- pending, paid, shipped, delivered, cancelled
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Order items
CREATE TABLE order_items (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  order_id UUID REFERENCES orders(id) ON DELETE CASCADE,
  product_id UUID REFERENCES products(id),
  variant_id UUID REFERENCES product_variants(id),
  quantity INTEGER NOT NULL,
  unit_price INTEGER NOT NULL, -- price at time of purchase
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for better performance
CREATE INDEX idx_products_category ON products(category);
CREATE INDEX idx_products_is_active ON products(is_active);
CREATE INDEX idx_product_variants_product_id ON product_variants(product_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_order_items_order_id ON order_items(order_id);

-- Updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at triggers
CREATE TRIGGER update_products_updated_at
  BEFORE UPDATE ON products
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_product_variants_updated_at
  BEFORE UPDATE ON product_variants
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_orders_updated_at
  BEFORE UPDATE ON orders
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Row Level Security (RLS)
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE product_variants ENABLE ROW LEVEL SECURITY;
ALTER TABLE admin_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE order_items ENABLE ROW LEVEL SECURITY;

-- Public read access for products (storefront)
CREATE POLICY "Products are viewable by everyone" ON products
  FOR SELECT USING (is_active = true);

CREATE POLICY "Product variants are viewable by everyone" ON product_variants
  FOR SELECT USING (true);

-- Service role has full access (for admin operations)
CREATE POLICY "Service role has full access to products" ON products
  FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role has full access to variants" ON product_variants
  FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role has full access to admin_users" ON admin_users
  FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role has full access to orders" ON orders
  FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role has full access to order_items" ON order_items
  FOR ALL USING (auth.role() = 'service_role');

-- Insert initial products (8 products from uploaded images)
INSERT INTO products (name, slug, category, color, price, image_url) VALUES
  -- Women (4 products)
  ('DRES KHAKI', 'dres-khaki', 'women', 'KHAKI', 44900, '/images/products/dres-khaki-kobieta.png'),
  ('SZARA BLUZA', 'szara-bluza', 'women', 'SZARY', 24900, '/images/products/szara-bluza-kobieta.png'),
  ('DRES GRAFITOWY', 'dres-grafitowy', 'women', 'GRAFITOWY', 39900, '/images/products/dres-grafitowy-kobieta.png'),
  ('TSHIRT CZARNY', 'tshirt-czarny-women', 'women', 'CZARNY', 13900, '/images/products/tshirt-czarny-kobieta.png'),
  -- Men (4 products)
  ('DRES CZARNY', 'dres-czarny', 'men', 'CZARNY', 44900, '/images/products/dres-czarny-mezczyzna.png'),
  ('KURTKA JEANSOWA CZARNA', 'kurtka-jeansowa', 'men', 'CZARNY', 32900, '/images/products/kurtka-jeansowa-mezczyzna.jpg'),
  ('TSHIRT CZARNY', 'tshirt-czarny-men', 'men', 'CZARNY', 14900, '/images/products/tshirt-czarny-mezczyzna.png'),
  ('BLUZA KHAKI', 'bluza-khaki', 'men', 'KHAKI', 27900, '/images/products/bluza-khaki-mezczyzna.jpg');

-- Insert default sizes for each product (10 items per size)
INSERT INTO product_variants (product_id, size, stock)
SELECT p.id, s.size, 10
FROM products p
CROSS JOIN (VALUES ('XS'), ('S'), ('M'), ('L'), ('XL')) AS s(size);
