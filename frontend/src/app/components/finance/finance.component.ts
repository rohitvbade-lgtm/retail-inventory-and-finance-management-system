import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { Invoice, DashboardStats } from '../../models/pos.models';

@Component({
  selector: 'app-finance',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './finance.component.html',
  styleUrls: ['./finance.component.css']
})
export class FinanceComponent implements OnInit {
  stats: DashboardStats = {
    total_products: 0,
    low_stock_count: 0,
    total_revenue: 0,
    total_invoices: 0,
    total_discounts_given: 0,
    active_discounts_count: 0
  };

  invoices: Invoice[] = [];
  searchQuery: string = '';
  loadingInvoices: boolean = false;

  selectedInvoice: Invoice | null = null;
  showInvoiceModal: boolean = false;

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.loadStats();
    this.loadInvoices();
  }

  loadStats(): void {
    this.api.getDashboardStats().subscribe({
      next: (data) => (this.stats = data),
      error: (err) => console.error('Failed to load dashboard stats', err)
    });
  }

  loadInvoices(): void {
    this.loadingInvoices = true;
    this.api.getInvoices(this.searchQuery).subscribe({
      next: (data) => {
        this.invoices = data;
        this.loadingInvoices = false;
      },
      error: (err) => {
        console.error('Failed to load invoices', err);
        this.loadingInvoices = false;
      }
    });
  }

  onSearchChange(): void {
    this.loadInvoices();
  }

  viewInvoice(inv: Invoice): void {
    this.selectedInvoice = inv;
    this.showInvoiceModal = true;
  }

  closeInvoiceModal(): void {
    this.showInvoiceModal = false;
    this.selectedInvoice = null;
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

