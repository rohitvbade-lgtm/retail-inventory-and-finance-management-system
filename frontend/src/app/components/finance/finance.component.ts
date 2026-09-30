import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subject } from 'rxjs';
import { debounceTime, distinctUntilChanged, takeUntil } from 'rxjs/operators';
import { ApiService } from '../../services/api.service';
import { Invoice, DashboardStats } from '../../models/pos.models';

@Component({
  selector: 'app-finance',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './finance.component.html',
  styleUrls: ['./finance.component.css'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class FinanceComponent implements OnInit, OnDestroy {
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

  // Pagination
  currentPage: number = 1;
  pageSize: number = 10;
  totalPages: number = 1;
  totalInvoices: number = 0;
  pageSizeOptions: number[] = [10, 25, 50];

  selectedInvoice: Invoice | null = null;
  showInvoiceModal: boolean = false;

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
        this.loadInvoices();
      });

    this.loadStats();
    this.loadInvoices();
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
    this.loadInvoices();
  }

  loadStats(): void {
    this.api.getDashboardStats().subscribe({
      next: (data) => {
        this.stats = data;
        this.cdr.markForCheck();
      },
      error: (err) => console.error('Failed to load dashboard stats', err)
    });
  }

  loadInvoices(): void {
    this.loadingInvoices = true;
    this.cdr.markForCheck();
    this.api.getInvoicesPaginated(this.searchQuery, this.currentPage, this.pageSize).subscribe({
      next: (data) => {
        this.invoices = data.items;
        this.totalInvoices = data.total;
        this.totalPages = data.total_pages;
        this.loadingInvoices = false;
        this.cdr.markForCheck();
      },
      error: (err) => {
        console.error('Failed to load invoices', err);
        this.loadingInvoices = false;
        this.cdr.markForCheck();
      }
    });
  }

  goToPage(page: number): void {
    if (page >= 1 && page <= this.totalPages && page !== this.currentPage) {
      this.currentPage = page;
      this.loadInvoices();
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
    this.loadInvoices();
  }

  viewInvoice(inv: Invoice): void {
    this.selectedInvoice = inv;
    this.showInvoiceModal = true;
    this.cdr.markForCheck();
  }

  closeInvoiceModal(): void {
    this.showInvoiceModal = false;
    this.selectedInvoice = null;
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

