import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { Product, CartItem, EvaluatedCartResponse, Invoice } from '../../models/pos.models';

@Component({
  selector: 'app-pos',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './pos.component.html',
  styleUrls: ['./pos.component.css']
})
export class PosComponent implements OnInit {
  products: Product[] = [];
  categories: string[] = [];
  selectedCategory: string = 'All';
  searchQuery: string = '';
  loadingProducts: boolean = false;

  cart: CartItem[] = [];
  cartPreview: EvaluatedCartResponse | null = null;
  evaluatingCart: boolean = false;

  customerName: string = 'Walk-in Customer';
  customerPhone: string = '';
  paymentMethod: string = 'Cash';
  notes: string = '';

  // Simulation controls to test weekend/weekday/seasonal discount rules
  simulationMode: string = 'CURRENT'; // 'CURRENT', 'WEEKEND', 'WEEKDAY', 'CUSTOM'
  customSimulatedDate: string = '';

  checkingOut: boolean = false;
  checkoutError: string | null = null;
  lastInvoice: Invoice | null = null;
  showReceiptModal: boolean = false;

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.loadProducts();
    this.loadCategories();
  }

  loadProducts(): void {
    this.loadingProducts = true;
    this.api.getProducts(this.searchQuery, this.selectedCategory).subscribe({
      next: (data) => {
        this.products = data;
        this.loadingProducts = false;
      },
      error: (err) => {
        console.error('Failed to load products', err);
        this.loadingProducts = false;
      }
    });
  }

  loadCategories(): void {
    this.api.getCategories().subscribe({
      next: (cats) => (this.categories = ['All', ...cats]),
      error: (err) => console.error('Failed to load categories', err)
    });
  }

  onCategorySelect(cat: string): void {
    this.selectedCategory = cat;
    this.loadProducts();
  }

  onSearchChange(): void {
    this.loadProducts();
  }

  addToCart(product: Product): void {
    if (product.quantity <= 0) return;

    const existing = this.cart.find((item) => item.product.id === product.id);
    if (existing) {
      if (existing.quantity < product.quantity) {
        existing.quantity += 1;
      }
    } else {
      this.cart.push({ product, quantity: 1 });
    }
    this.refreshCartPreview();
  }

  incrementQuantity(item: CartItem): void {
    if (item.quantity < item.product.quantity) {
      item.quantity += 1;
      this.refreshCartPreview();
    }
  }

  decrementQuantity(item: CartItem): void {
    if (item.quantity > 1) {
      item.quantity -= 1;
    } else {
      this.removeFromCart(item);
      return;
    }
    this.refreshCartPreview();
  }

  removeFromCart(item: CartItem): void {
    this.cart = this.cart.filter((c) => c.product.id !== item.product.id);
    this.refreshCartPreview();
  }

  clearCart(): void {
    this.cart = [];
    this.cartPreview = null;
  }

  getSimulatedDateIso(): string | undefined {
    const now = new Date();
    if (this.simulationMode === 'WEEKEND') {
      // Return coming or recent Saturday
      const day = now.getDay();
      const diff = 6 - day; // Target Saturday
      const sat = new Date(now);
      sat.setDate(now.getDate() + diff);
      return sat.toISOString();
    } else if (this.simulationMode === 'WEEKDAY') {
      // Target Wednesday
      const day = now.getDay();
      const diff = 3 - day;
      const wed = new Date(now);
      wed.setDate(now.getDate() + diff);
      return wed.toISOString();
    } else if (this.simulationMode === 'CUSTOM' && this.customSimulatedDate) {
      return new Date(this.customSimulatedDate).toISOString();
    }
    return undefined;
  }

  onSimulationChange(): void {
    this.refreshCartPreview();
  }

  refreshCartPreview(): void {
    if (this.cart.length === 0) {
      this.cartPreview = null;
      return;
    }

    this.evaluatingCart = true;
    const itemsPayload = this.cart.map((c) => ({
      product_id: c.product.id,
      quantity: c.quantity
    }));

    this.api.previewCart(itemsPayload, this.getSimulatedDateIso()).subscribe({
      next: (preview) => {
        this.cartPreview = preview;
        this.evaluatingCart = false;
      },
      error: (err) => {
        console.error('Failed to preview cart', err);
        this.evaluatingCart = false;
      }
    });
  }

  completeCheckout(): void {
    if (this.cart.length === 0) return;
    this.checkingOut = true;
    this.checkoutError = null;

    const payload = {
      customer_name: this.customerName || 'Walk-in Customer',
      customer_phone: this.customerPhone || undefined,
      items: this.cart.map((c) => ({ product_id: c.product.id, quantity: c.quantity })),
      payment_method: this.paymentMethod,
      notes: this.notes || undefined,
      simulated_date_iso: this.getSimulatedDateIso()
    };

    this.api.checkoutInvoice(payload).subscribe({
      next: (invoice) => {
        this.lastInvoice = invoice;
        this.showReceiptModal = true;
        this.checkingOut = false;
        this.clearCart();
        this.loadProducts(); // refresh stock numbers
      },
      error: (err) => {
        this.checkingOut = false;
        this.checkoutError = err.error?.detail || 'Checkout failed. Please check stock and try again.';
      }
    });
  }

  closeReceiptModal(): void {
    this.showReceiptModal = false;
    this.lastInvoice = null;
  }

  printReceipt(): void {
    window.print();
  }

  parseDiscountBreakdown(jsonStr?: string): any[] {
    if (!jsonStr) return [];
    try {
      return JSON.parse(jsonStr);
    } catch {
      return [];
    }
  }
}

