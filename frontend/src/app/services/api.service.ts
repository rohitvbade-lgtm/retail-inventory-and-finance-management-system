import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, Subject } from 'rxjs';
import {
  Product,
  DiscountRule,
  EvaluatedCartResponse,
  Invoice,
  DashboardStats,
  ChatMessage,
  ChatPromptResponse,
  PaginatedResponse,
  PaginatedDiscountResponse
} from '../models/pos.models';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private baseUrl = 'http://localhost:8000/api';

  // Event stream for instant low stock alert updates
  public alertsUpdated$ = new Subject<void>();

  constructor(private http: HttpClient) {}

  triggerAlertsRefresh(): void {
    this.alertsUpdated$.next();
  }

  // ---------------- INVENTORY ----------------
  getProductsPaginated(
    search?: string,
    category?: string,
    lowStockOnly: boolean = false,
    page: number = 1,
    pageSize: number = 12
  ): Observable<PaginatedResponse<Product>> {
    let params = new HttpParams()
      .set('page', page.toString())
      .set('page_size', pageSize.toString());

    if (search && search.trim()) params = params.set('search', search.trim());
    if (category && category !== 'All') params = params.set('category', category);
    if (lowStockOnly) params = params.set('low_stock_only', 'true');
    return this.http.get<PaginatedResponse<Product>>(`${this.baseUrl}/products`, { params });
  }

  getProducts(search?: string, category?: string, lowStockOnly: boolean = false): Observable<Product[]> {
    let params = new HttpParams();
    if (search && search.trim()) params = params.set('search', search.trim());
    if (category && category !== 'All') params = params.set('category', category);
    if (lowStockOnly) params = params.set('low_stock_only', 'true');
    return this.http.get<Product[]>(`${this.baseUrl}/products`, { params });
  }

  getLowStockAlerts(): Observable<Product[]> {
    return this.http.get<Product[]>(`${this.baseUrl}/products/low-stock/alerts`);
  }

  getCategories(): Observable<string[]> {
    return this.http.get<string[]>(`${this.baseUrl}/products/categories`);
  }

  createProduct(product: Partial<Product>): Observable<Product> {
    return this.http.post<Product>(`${this.baseUrl}/products`, product);
  }

  updateProduct(id: number, product: Partial<Product>): Observable<Product> {
    return this.http.put<Product>(`${this.baseUrl}/products/${id}`, product);
  }

  adjustStock(id: number, delta: number, reason: string = 'Counter restock'): Observable<Product> {
    return this.http.patch<Product>(`${this.baseUrl}/products/${id}/stock`, {
      quantity_delta: delta,
      reason
    });
  }

  deleteProduct(id: number): Observable<{ message: string }> {
    return this.http.delete<{ message: string }>(`${this.baseUrl}/products/${id}`);
  }

  // ---------------- DISCOUNTS ----------------
  getDiscountRules(
    tab: 'active' | 'expired' | 'all' = 'all',
    search?: string
  ): Observable<DiscountRule[]> {
    let params = new HttpParams().set('tab', tab);
    if (search && search.trim()) params = params.set('search', search.trim());
    return this.http.get<DiscountRule[]>(`${this.baseUrl}/discounts`, { params });
  }

  getDiscountRulesPaginated(
    tab: 'active' | 'expired' | 'all' = 'all',
    search?: string,
    page: number = 1,
    pageSize: number = 10
  ): Observable<PaginatedDiscountResponse> {
    let params = new HttpParams()
      .set('tab', tab)
      .set('page', page.toString())
      .set('page_size', pageSize.toString());
    if (search && search.trim()) params = params.set('search', search.trim());
    return this.http.get<PaginatedDiscountResponse>(`${this.baseUrl}/discounts`, { params });
  }

  createDiscountRule(rule: Partial<DiscountRule>): Observable<DiscountRule> {
    return this.http.post<DiscountRule>(`${this.baseUrl}/discounts`, rule);
  }

  toggleDiscountRule(id: number): Observable<DiscountRule> {
    return this.http.patch<DiscountRule>(`${this.baseUrl}/discounts/${id}/toggle`, {});
  }

  deleteDiscountRule(id: number): Observable<{ message: string }> {
    return this.http.delete<{ message: string }>(`${this.baseUrl}/discounts/${id}`);
  }

  evaluateCart(
    items: { product_id: number; quantity: number }[],
    simulatedDate?: string,
    promoCode?: string
  ): Observable<EvaluatedCartResponse> {
    return this.http.post<EvaluatedCartResponse>(`${this.baseUrl}/discounts/evaluate`, {
      items,
      simulated_date_iso: simulatedDate || null,
      promo_code: promoCode || null
    });
  }

  // ---------------- FINANCE & POS ----------------
  previewCart(
    items: { product_id: number; quantity: number }[],
    simulatedDate?: string,
    promoCode?: string
  ): Observable<EvaluatedCartResponse> {
    return this.http.post<EvaluatedCartResponse>(`${this.baseUrl}/finance/preview`, {
      items,
      simulated_date_iso: simulatedDate || null,
      promo_code: promoCode || null
    });
  }

  checkoutInvoice(data: {
    customer_name?: string;
    customer_phone?: string;
    customer_email?: string;
    items: { product_id: number; quantity: number }[];
    payment_method: string;
    notes?: string;
    simulated_date_iso?: string;
    promo_code?: string;
  }): Observable<Invoice> {
    return this.http.post<Invoice>(`${this.baseUrl}/finance/checkout`, data);
  }

  getInvoicesPaginated(
    search?: string,
    page: number = 1,
    pageSize: number = 10
  ): Observable<PaginatedResponse<Invoice>> {
    let params = new HttpParams()
      .set('page', page.toString())
      .set('page_size', pageSize.toString());
    if (search && search.trim()) params = params.set('search', search.trim());
    return this.http.get<PaginatedResponse<Invoice>>(`${this.baseUrl}/finance/invoices`, { params });
  }

  getInvoices(search?: string): Observable<Invoice[]> {
    let params = new HttpParams();
    if (search && search.trim()) params = params.set('search', search.trim());
    return this.http.get<Invoice[]>(`${this.baseUrl}/finance/invoices`, { params });
  }

  getInvoice(id: number): Observable<Invoice> {
    return this.http.get<Invoice>(`${this.baseUrl}/finance/invoices/${id}`);
  }

  getDashboardStats(): Observable<DashboardStats> {
    return this.http.get<DashboardStats>(`${this.baseUrl}/finance/dashboard/stats`);
  }

  // ---------------- AI DISCOUNT MACHINE CHAT ----------------
  sendChatMessage(message: string, apiKey?: string): Observable<ChatPromptResponse> {
    return this.http.post<ChatPromptResponse>(`${this.baseUrl}/ai/chat`, {
      message,
      api_key: apiKey || null
    });
  }

  getChatHistory(): Observable<ChatMessage[]> {
    return this.http.get<ChatMessage[]>(`${this.baseUrl}/ai/history`);
  }
}

