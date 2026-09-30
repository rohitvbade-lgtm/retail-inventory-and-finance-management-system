import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subject } from 'rxjs';
import { debounceTime, distinctUntilChanged, takeUntil } from 'rxjs/operators';
import { ApiService } from '../../services/api.service';
import { Product, CartItem, EvaluatedCartResponse, Invoice } from '../../models/pos.models';

@Component({
  selector: 'app-pos',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './pos.component.html',
  styleUrls: ['./pos.component.css'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class PosComponent implements OnInit, OnDestroy {
  products: Product[] = [];
  categories: string[] = [];
  selectedCategory: string = 'All';
  searchQuery: string = '';
  loadingProducts: boolean = false;

  // Pagination
  currentPage: number = 1;
  pageSize: number = 12;
  totalPages: number = 1;
  totalProducts: number = 0;

  // Cart & Promo
  cart: CartItem[] = [];
  cartPreview: EvaluatedCartResponse | null = null;
  evaluatingCart: boolean = false;
  enteredPromoCode: string = '';
  appliedPromoCode: string = '';
  promoCodeStatus: string | null = null;

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

  private searchSubject = new Subject<string>();
  private destroy$ = new Subject<void>();

  constructor(
    private api: ApiService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.searchSubject
      .pipe(
        debounceTime(250),
        distinctUntilChanged(),
        takeUntil(this.destroy$)
      )
      .subscribe((query) => {
        this.searchQuery = query;
        this.currentPage = 1;
        this.loadProducts();
      });

    this.loadProducts();
    this.loadCategories();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  onSearchInput(val: string): void {
    this.searchSubject.next(val);
  }

  clearSearch(): void {
    this.searchQuery = '';
    this.currentPage = 1;
    this.loadProducts();
  }

  loadProducts(): void {
    this.loadingProducts = true;
    this.cdr.markForCheck();
    this.api
      .getProductsPaginated(this.searchQuery, this.selectedCategory, false, this.currentPage, this.pageSize)
      .subscribe({
        next: (data) => {
          this.products = data.items;
          this.totalProducts = data.total;
          this.totalPages = data.total_pages;
          this.loadingProducts = false;
          this.cdr.markForCheck();
        },
        error: (err) => {
          console.error('Failed to load products', err);
          this.loadingProducts = false;
          this.cdr.markForCheck();
        }
      });
  }

  goToPage(page: number): void {
    if (page >= 1 && page <= this.totalPages && page !== this.currentPage) {
      this.currentPage = page;
      this.loadProducts();
    }
  }

  nextPage(): void {
    if (this.currentPage < this.totalPages) {
      this.goToPage(this.currentPage + 1);
    }
  }

  prevPage(): void {
    if (this.currentPage > 1) {
      this.goToPage(this.currentPage - 1);
    }
  }

  loadCategories(): void {
    this.api.getCategories().subscribe({
      next: (cats) => {
        this.categories = ['All', ...cats];
        this.cdr.markForCheck();
      },
      error: (err) => console.error('Failed to load categories', err)
    });
  }

  onCategorySelect(cat: string): void {
    this.selectedCategory = cat;
    this.currentPage = 1;
    this.loadProducts();
  }

  applyPromoCode(): void {
    if (!this.enteredPromoCode.trim()) return;
    this.appliedPromoCode = this.enteredPromoCode.trim().toUpperCase();
    this.refreshCartPreview();
  }

  removePromoCode(): void {
    this.enteredPromoCode = '';
    this.appliedPromoCode = '';
    this.promoCodeStatus = null;
    this.refreshCartPreview();
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
    this.cdr.markForCheck();
  }

  incrementQuantity(item: CartItem): void {
    if (item.quantity < item.product.quantity) {
      item.quantity += 1;
      this.refreshCartPreview();
      this.cdr.markForCheck();
    }
  }

  decrementQuantity(item: CartItem): void {
    if (item.quantity > 1) {
      item.quantity -= 1;
      this.refreshCartPreview();
      this.cdr.markForCheck();
    } else {
      this.removeFromCart(item);
    }
  }

  removeFromCart(item: CartItem): void {
    this.cart = this.cart.filter((c) => c.product.id !== item.product.id);
    this.refreshCartPreview();
    this.cdr.markForCheck();
  }

  clearCart(): void {
    this.cart = [];
    this.cartPreview = null;
    this.appliedPromoCode = '';
    this.enteredPromoCode = '';
    this.promoCodeStatus = null;
    this.cdr.markForCheck();
  }

  getSimulatedDateIso(): string | undefined {
    const now = new Date();
    if (this.simulationMode === 'WEEKEND') {
      const day = now.getDay();
      const diff = 6 - day;
      const sat = new Date(now);
      sat.setDate(now.getDate() + diff);
      return sat.toISOString();
    } else if (this.simulationMode === 'WEEKDAY') {
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
      this.evaluatingCart = false;
      this.cdr.markForCheck();
      return;
    }

    this.evaluatingCart = true;
    this.cdr.markForCheck();
    const itemsPayload = this.cart.map((c) => ({
      product_id: c.product.id,
      quantity: c.quantity
    }));

    this.api.previewCart(itemsPayload, this.getSimulatedDateIso(), this.appliedPromoCode).subscribe({
      next: (preview) => {
        this.cartPreview = preview;
        this.promoCodeStatus = preview.promo_code_status || null;
        this.evaluatingCart = false;
        this.cdr.markForCheck();
      },
      error: (err) => {
        console.error('Failed to preview cart', err);
        this.evaluatingCart = false;
        this.cdr.markForCheck();
      }
    });
  }

  completeCheckout(): void {
    if (this.cart.length === 0) return;
    this.checkingOut = true;
    this.checkoutError = null;
    this.cdr.markForCheck();

    const payload = {
      customer_name: this.customerName || 'Walk-in Customer',
      customer_phone: this.customerPhone || undefined,
      items: this.cart.map((c) => ({ product_id: c.product.id, quantity: c.quantity })),
      payment_method: this.paymentMethod,
      notes: this.notes || undefined,
      simulated_date_iso: this.getSimulatedDateIso(),
      promo_code: this.appliedPromoCode || undefined
    };

    this.api.checkoutInvoice(payload).subscribe({
      next: (invoice) => {
        this.lastInvoice = invoice;
        this.showReceiptModal = true;
        this.checkingOut = false;
        this.clearCart();
        this.loadProducts(); // refresh stock numbers
        this.api.triggerAlertsRefresh(); // update top navbar alert count
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.checkingOut = false;
        this.checkoutError = err.error?.detail || 'Checkout failed. Please check stock and try again.';
        this.cdr.markForCheck();
      }
    });
  }

  closeReceiptModal(): void {
    this.showReceiptModal = false;
    this.lastInvoice = null;
    this.cdr.markForCheck();
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

