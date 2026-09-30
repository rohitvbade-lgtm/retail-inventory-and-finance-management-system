export interface Product {
  id: number;
  name: str;
  sku: string;
  category: string;
  price: number;
  cost_price: number;
  quantity: number;
  min_threshold: number;
  description?: string;
  is_low_stock: boolean;
  created_at: string;
  updated_at: string;
}

export type str = string;

export interface DiscountRule {
  id: number;
  name: string;
  description?: string;
  discount_type: 'PERCENTAGE' | 'FIXED_AMOUNT';
  value: number;
  applicability: 'PRODUCT' | 'CATEGORY' | 'ENTIRE_ORDER';
  target_products: any[];
  target_categories: string[];
  min_order_amount: number;
  schedule_type: 'ALWAYS' | 'WEEKEND' | 'WEEKDAY' | 'DATE_RANGE';
  start_date?: string;
  end_date?: string;
  is_active: boolean;
  created_by?: string;
  created_at: string;
  updated_at: string;
}

export interface CartItem {
  product: Product;
  quantity: number;
}

export interface EvaluatedCartItem {
  product_id: number;
  name: string;
  category: string;
  unit_price: number;
  quantity: number;
  item_subtotal: number;
  discount_amount: number;
  final_item_total: number;
  applied_discount_name?: string;
}

export interface AppliedDiscountDetail {
  rule_id: number;
  rule_name: string;
  description?: string;
  discount_amount: number;
  applicability: string;
  applied_to: string;
}

export interface EvaluatedCartResponse {
  subtotal: number;
  total_discount: number;
  tax: number;
  total: number;
  line_items: EvaluatedCartItem[];
  applied_discounts: AppliedDiscountDetail[];
}

export interface InvoiceItem {
  id?: number;
  product_id?: number;
  product_name: string;
  category?: string;
  unit_price: number;
  quantity: number;
  item_subtotal: number;
  discount_amount: number;
  item_total: number;
  applied_discount_name?: string;
}

export interface Invoice {
  id: number;
  invoice_number: string;
  customer_name: string;
  customer_phone?: string;
  customer_email?: string;
  subtotal: number;
  discount_total: number;
  tax: number;
  total: number;
  payment_method: string;
  notes?: string;
  discount_breakdown?: string;
  created_at: string;
  items: InvoiceItem[];
}

export interface DashboardStats {
  total_products: number;
  low_stock_count: number;
  total_revenue: number;
  total_invoices: number;
  total_discounts_given: number;
  active_discounts_count: number;
}

export interface ChatMessage {
  id?: number;
  role: 'user' | 'assistant';
  content: string;
  structured_action?: any;
  created_at?: string;
}

export interface ChatPromptResponse {
  reply: string;
  action_type: string;
  created_discount?: DiscountRule;
  active_discounts?: DiscountRule[];
}

