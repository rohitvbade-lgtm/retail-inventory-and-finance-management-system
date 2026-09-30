import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subject } from 'rxjs';
import { debounceTime, distinctUntilChanged, takeUntil } from 'rxjs/operators';
import { ApiService } from '../../services/api.service';
import { Product } from '../../models/pos.models';

@Component({
  selector: 'app-inventory',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './inventory.component.html',
  styleUrls: ['./inventory.component.css'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class InventoryComponent implements OnInit, OnDestroy {
  products: Product[] = [];
  lowStockProducts: Product[] = [];
  categories: string[] = [];

  searchQuery: string = '';
  selectedCategory: string = 'All';
  lowStockOnly: boolean = false;
  loading: boolean = false;

  // Pagination
  currentPage: number = 1;
  pageSize: number = 10;
  totalPages: number = 1;
  totalProducts: number = 0;
  pageSizeOptions: number[] = [10, 25, 50];

  // Modals state
  showProductModal: boolean = false;
  isEditing: boolean = false;
  editingProductId: number | null = null;

  productForm: Partial<Product> = {
    name: '',
    sku: '',
    category: 'General',
    price: 0,
    cost_price: 0,
    quantity: 0,
    min_threshold: 5,
    description: ''
  };

  showRestockModal: boolean = false;
  selectedProductForRestock: Product | null = null;
  restockDelta: number = 10;
  restockReason: string = 'Routine inventory restock';

  errorMessage: string | null = null;
  Math = Math;

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
    this.loadLowStockAlerts();
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
    this.loading = true;
    this.cdr.markForCheck();
    this.api
      .getProductsPaginated(
        this.searchQuery,
        this.selectedCategory,
        this.lowStockOnly,
        this.currentPage,
        this.pageSize
      )
      .subscribe({
        next: (data) => {
          this.products = data.items;
          this.totalProducts = data.total;
          this.totalPages = data.total_pages;
          this.loading = false;
          this.cdr.markForCheck();
        },
        error: (err) => {
          console.error('Failed to load products', err);
          this.loading = false;
          this.cdr.markForCheck();
        }
      });
  }

  loadLowStockAlerts(): void {
    this.api.getLowStockAlerts().subscribe({
      next: (alerts) => {
        this.lowStockProducts = alerts;
        this.cdr.markForCheck();
      },
      error: (err) => console.error('Failed to load low stock alerts', err)
    });
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

  onFilterChange(): void {
    this.currentPage = 1;
    this.loadProducts();
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

  onPageSizeChange(newSize: number): void {
    this.pageSize = Number(newSize);
    this.currentPage = 1;
    this.loadProducts();
  }

  openAddProductModal(): void {
    this.isEditing = false;
    this.editingProductId = null;
    this.productForm = {
      name: '',
      sku: 'SKU-' + Math.floor(1000 + Math.random() * 9000),
      category: 'General',
      price: 0.0,
      cost_price: 0.0,
      quantity: 10,
      min_threshold: 5,
      description: ''
    };
    this.errorMessage = null;
    this.showProductModal = true;
    this.cdr.markForCheck();
  }

  openEditProductModal(prod: Product): void {
    this.isEditing = true;
    this.editingProductId = prod.id;
    this.productForm = { ...prod };
    this.errorMessage = null;
    this.showProductModal = true;
    this.cdr.markForCheck();
  }

  saveProduct(): void {
    this.errorMessage = null;
    if (!this.productForm.name || !this.productForm.sku) {
      this.errorMessage = 'Name and SKU are required fields.';
      this.cdr.markForCheck();
      return;
    }

    if (this.isEditing && this.editingProductId) {
      this.api.updateProduct(this.editingProductId, this.productForm).subscribe({
        next: () => {
          this.showProductModal = false;
          this.loadProducts();
          this.loadLowStockAlerts();
          this.api.triggerAlertsRefresh();
          this.cdr.markForCheck();
        },
        error: (err) => {
          this.errorMessage = err.error?.detail || 'Failed to update product.';
          this.cdr.markForCheck();
        }
      });
    } else {
      this.api.createProduct(this.productForm).subscribe({
        next: () => {
          this.showProductModal = false;
          this.loadProducts();
          this.loadLowStockAlerts();
          this.api.triggerAlertsRefresh();
          this.cdr.markForCheck();
        },
        error: (err) => {
          this.errorMessage = err.error?.detail || 'Failed to create product.';
          this.cdr.markForCheck();
        }
      });
    }
  }

  openRestockModal(prod: Product): void {
    this.selectedProductForRestock = prod;
    this.restockDelta = 10;
    this.showRestockModal = true;
    this.cdr.markForCheck();
  }

  submitRestock(): void {
    if (!this.selectedProductForRestock) return;
    this.api
      .adjustStock(
        this.selectedProductForRestock.id,
        this.restockDelta,
        this.restockReason
      )
      .subscribe({
        next: () => {
          this.showRestockModal = false;
          this.selectedProductForRestock = null;
          this.loadProducts();
          this.loadLowStockAlerts();
          this.api.triggerAlertsRefresh();
          this.cdr.markForCheck();
        },
        error: (err) => {
          console.error('Failed to adjust stock', err);
          this.cdr.markForCheck();
        }
      });
  }

  deleteProduct(prod: Product): void {
    if (confirm(`Are you sure you want to delete '${prod.name}'?`)) {
      this.api.deleteProduct(prod.id).subscribe({
        next: () => {
          this.loadProducts();
          this.loadLowStockAlerts();
          this.api.triggerAlertsRefresh();
          this.cdr.markForCheck();
        },
        error: (err) => {
          console.error('Failed to delete product', err);
          this.cdr.markForCheck();
        }
      });
    }
  }
}
