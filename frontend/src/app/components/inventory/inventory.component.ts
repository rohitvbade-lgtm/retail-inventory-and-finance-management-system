import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { Product } from '../../models/pos.models';

@Component({
  selector: 'app-inventory',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './inventory.component.html',
  styleUrls: ['./inventory.component.css']
})
export class InventoryComponent implements OnInit {
  products: Product[] = [];
  lowStockProducts: Product[] = [];
  categories: string[] = [];

  searchQuery: string = '';
  selectedCategory: string = 'All';
  lowStockOnly: boolean = false;
  loading: boolean = false;

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

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.loadProducts();
    this.loadLowStockAlerts();
    this.loadCategories();
  }

  loadProducts(): void {
    this.loading = true;
    this.api.getProducts(this.searchQuery, this.selectedCategory, this.lowStockOnly).subscribe({
      next: (data) => {
        this.products = data;
        this.loading = false;
      },
      error: (err) => {
        console.error('Failed to load products', err);
        this.loading = false;
      }
    });
  }

  loadLowStockAlerts(): void {
    this.api.getLowStockAlerts().subscribe({
      next: (alerts) => (this.lowStockProducts = alerts),
      error: (err) => console.error('Failed to load low stock alerts', err)
    });
  }

  loadCategories(): void {
    this.api.getCategories().subscribe({
      next: (cats) => (this.categories = ['All', ...cats]),
      error: (err) => console.error('Failed to load categories', err)
    });
  }

  onFilterChange(): void {
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
  }

  openEditProductModal(prod: Product): void {
    this.isEditing = true;
    this.editingProductId = prod.id;
    this.productForm = { ...prod };
    this.errorMessage = null;
    this.showProductModal = true;
  }

  saveProduct(): void {
    this.errorMessage = null;
    if (!this.productForm.name || !this.productForm.sku) {
      this.errorMessage = 'Name and SKU are required fields.';
      return;
    }

    if (this.isEditing && this.editingProductId) {
      this.api.updateProduct(this.editingProductId, this.productForm).subscribe({
        next: () => {
          this.showProductModal = false;
          this.loadProducts();
          this.loadLowStockAlerts();
        },
        error: (err) => (this.errorMessage = err.error?.detail || 'Failed to update product.')
      });
    } else {
      this.api.createProduct(this.productForm).subscribe({
        next: () => {
          this.showProductModal = false;
          this.loadProducts();
          this.loadLowStockAlerts();
        },
        error: (err) => (this.errorMessage = err.error?.detail || 'Failed to create product.')
      });
    }
  }

  openRestockModal(prod: Product): void {
    this.selectedProductForRestock = prod;
    this.restockDelta = 10;
    this.showRestockModal = true;
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
        },
        error: (err) => console.error('Failed to adjust stock', err)
      });
  }

  deleteProduct(prod: Product): void {
    if (confirm(`Are you sure you want to delete '${prod.name}'?`)) {
      this.api.deleteProduct(prod.id).subscribe({
        next: () => {
          this.loadProducts();
          this.loadLowStockAlerts();
        },
        error: (err) => console.error('Failed to delete product', err)
      });
    }
  }
}
