import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { Subject } from 'rxjs';
import { debounceTime, distinctUntilChanged, takeUntil } from 'rxjs/operators';
import { ApiService } from '../../services/api.service';
import {
  DiscountRule,
  ChatMessage,
  Product,
  EvaluatedCartResponse
} from '../../models/pos.models';

@Component({
  selector: 'app-discounts',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './discounts.component.html',
  styleUrls: ['./discounts.component.css'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class DiscountsComponent implements OnInit, OnDestroy {
  // View mode switcher: 'codes' (full codes directory), 'ai' (AI chat engine), 'split' (side-by-side)
  activeView: 'codes' | 'ai' | 'split' = 'codes';
  editingExpiryRuleId: number | null = null;
  customExpiryInput: string = '';

  chatMessages: ChatMessage[] = [];
  promptInput: string = '';
  apiKey: string = '';
  showApiKeyInput: boolean = false;
  sendingMessage: boolean = false;

  // Rules Tabs & Pagination
  rules: DiscountRule[] = [];
  loadingRules: boolean = false;
  selectedTab: 'active' | 'expired' | 'all' = 'active';
  rulesSearchQuery: string = '';
  activeCount: number = 0;
  expiredCount: number = 0;
  totalRules: number = 0;
  currentPage: number = 1;
  pageSize: number = 6;
  totalPages: number = 1;
  copiedCode: string | null = null;

  // Manual Rule Creation Modal
  showCreateModal: boolean = false;
  createError: string | null = null;
  categories: string[] = [];
  selectedTargetCategory: string = 'General';
  newRuleForm: Partial<DiscountRule> = {
    name: '',
    code: '',
    discount_type: 'PERCENTAGE',
    value: 10,
    applicability: 'CATEGORY',
    min_order_amount: 0,
    schedule_type: 'WEEKEND',
    start_date: '',
    end_date: '',
    description: ''
  };

  // Simulator test bench
  products: Product[] = [];
  simSelectedProductIds: { [key: number]: number } = {};
  simSchedule: string = 'WEEKEND'; // 'WEEKEND', 'WEEKDAY', 'ALWAYS'
  simResult: EvaluatedCartResponse | null = null;
  evaluatingSim: boolean = false;

  suggestedPrompts = [
    'Give 15% discount on all dairy products this weekend',
    'Apply 10% off on Beverages and Snacks on weekdays',
    'Flat $5 discount on orders over $40',
    'Give 20% discount on Bakery products until tomorrow',
    'What discounts are currently active?',
    'Deactivate all weekend discounts'
  ];

  private rulesSearchSubject = new Subject<string>();
  private destroy$ = new Subject<void>();

  constructor(
    private api: ApiService,
    private cdr: ChangeDetectorRef,
    private route: ActivatedRoute
  ) {}

  ngOnInit(): void {
    const savedKey = localStorage.getItem('gemini_api_key');
    if (savedKey) this.apiKey = savedKey;

    this.route.queryParams.pipe(takeUntil(this.destroy$)).subscribe((params) => {
      if (params['view'] === 'ai') {
        this.activeView = 'ai';
      } else if (params['view'] === 'codes') {
        this.activeView = 'codes';
      } else if (params['view'] === 'split') {
        this.activeView = 'split';
      }
      this.cdr.markForCheck();
    });

    this.rulesSearchSubject
      .pipe(
        debounceTime(250),
        distinctUntilChanged(),
        takeUntil(this.destroy$)
      )
      .subscribe((query) => {
        this.rulesSearchQuery = query;
        this.currentPage = 1;
        this.loadRules();
      });

    this.loadRules();
    this.loadChatHistory();
    this.loadProductsForSimulator();
    this.loadCategories();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  loadCategories(): void {
    this.api.getCategories().subscribe({
      next: (cats) => {
        this.categories = cats;
        if (cats.length > 0) this.selectedTargetCategory = cats[0];
        this.cdr.markForCheck();
      },
      error: () => {}
    });
  }

  selectTab(tab: 'active' | 'expired' | 'all'): void {
    this.selectedTab = tab;
    this.currentPage = 1;
    this.loadRules();
  }

  onRulesSearchInput(val: string): void {
    this.rulesSearchSubject.next(val);
  }

  clearRulesSearch(): void {
    this.rulesSearchQuery = '';
    this.currentPage = 1;
    this.loadRules();
  }

  loadRules(): void {
    this.loadingRules = true;
    this.cdr.markForCheck();
    this.api
      .getDiscountRulesPaginated(
        this.selectedTab,
        this.rulesSearchQuery,
        this.currentPage,
        this.pageSize
      )
      .subscribe({
        next: (data) => {
          this.rules = data.items;
          this.activeCount = data.active_count;
          this.expiredCount = data.expired_count;
          this.totalRules = data.total;
          this.totalPages = data.total_pages;
          this.loadingRules = false;
          this.cdr.markForCheck();
        },
        error: (err) => {
          console.error('Failed to load rules', err);
          this.loadingRules = false;
          this.cdr.markForCheck();
        }
      });
  }

  goToPage(page: number): void {
    if (page >= 1 && page <= this.totalPages && page !== this.currentPage) {
      this.currentPage = page;
      this.loadRules();
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

  copyCode(code?: string): void {
    if (!code) return;
    navigator.clipboard.writeText(code).then(() => {
      this.copiedCode = code;
      this.cdr.markForCheck();
      setTimeout(() => {
        this.copiedCode = null;
        this.cdr.markForCheck();
      }, 2000);
    });
  }

  openCreateModal(): void {
    this.createError = null;
    this.newRuleForm = {
      name: '',
      code: 'PROMO' + Math.floor(10 + Math.random() * 90),
      discount_type: 'PERCENTAGE',
      value: 15,
      applicability: 'CATEGORY',
      target_categories: this.categories.length > 0 ? [this.categories[0]] : ['General'],
      min_order_amount: 0,
      schedule_type: 'WEEKEND',
      start_date: '',
      end_date: '',
      description: ''
    };
    this.showCreateModal = true;
    this.cdr.markForCheck();
  }

  closeCreateModal(): void {
    this.showCreateModal = false;
    this.createError = null;
    this.cdr.markForCheck();
  }

  submitCreateRule(): void {
    this.createError = null;
    if (!this.newRuleForm.name?.trim()) {
      this.createError = 'Rule name is required.';
      this.cdr.markForCheck();
      return;
    }

    const payload: Partial<DiscountRule> = {
      ...this.newRuleForm,
      code: this.newRuleForm.code?.trim().toUpperCase(),
      target_categories: this.newRuleForm.applicability === 'CATEGORY' ? [this.selectedTargetCategory] : [],
      is_active: true
    };

    this.api.createDiscountRule(payload).subscribe({
      next: () => {
        this.showCreateModal = false;
        this.loadRules();
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.createError = err.error?.detail || 'Failed to create discount rule.';
        this.cdr.markForCheck();
      }
    });
  }

  loadChatHistory(): void {
    this.api.getChatHistory().subscribe({
      next: (msgs) => {
        this.chatMessages = msgs;
        this.scrollToBottom();
        this.cdr.markForCheck();
      },
      error: (err) => console.error('Failed to load chat history', err)
    });
  }

  loadProductsForSimulator(): void {
    this.api.getProducts().subscribe({
      next: (prods) => {
        this.products = prods;
        // Pre-select 2 sample products for quick simulation
        if (prods.length >= 2) {
          this.simSelectedProductIds[prods[0].id] = 2;
          this.simSelectedProductIds[prods[1].id] = 1;
        }
        this.cdr.markForCheck();
      },
      error: (err) => console.error('Failed to load products for simulator', err)
    });
  }

  saveApiKey(): void {
    if (this.apiKey) {
      localStorage.setItem('gemini_api_key', this.apiKey.trim());
    } else {
      localStorage.removeItem('gemini_api_key');
    }
  }

  usePrompt(prompt: string): void {
    this.promptInput = prompt;
    this.sendPrompt();
  }

  sendPrompt(): void {
    const text = this.promptInput.trim();
    if (!text || this.sendingMessage) return;

    this.sendingMessage = true;
    this.chatMessages.push({
      role: 'user',
      content: text
    });
    this.promptInput = '';
    this.scrollToBottom();
    this.cdr.markForCheck();

    this.api.sendChatMessage(text, this.apiKey).subscribe({
      next: (res) => {
        this.chatMessages.push({
          role: 'assistant',
          content: res.reply,
          structured_action: res.created_discount || null
        });
        this.sendingMessage = false;
        this.loadRules(); // Refresh active rules table
        this.scrollToBottom();
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.chatMessages.push({
          role: 'assistant',
          content: 'Sorry, I encountered an error processing that instruction. Please try again.'
        });
        this.sendingMessage = false;
        this.scrollToBottom();
        this.cdr.markForCheck();
      }
    });
  }

  // Simulator test
  runSimulation(): void {
    const items = Object.entries(this.simSelectedProductIds)
      .filter(([_, qty]) => qty > 0)
      .map(([idStr, qty]) => ({ product_id: parseInt(idStr, 10), quantity: qty }));

    if (items.length === 0) {
      alert('Please select at least one item quantity for the test basket.');
      return;
    }

    this.evaluatingSim = true;
    this.cdr.markForCheck();
    let simDateIso: string | undefined = undefined;
    const now = new Date();

    if (this.simSchedule === 'WEEKEND') {
      const day = now.getDay();
      const diff = 6 - day; // Saturday
      const sat = new Date(now);
      sat.setDate(now.getDate() + diff);
      simDateIso = sat.toISOString();
    } else if (this.simSchedule === 'WEEKDAY') {
      const day = now.getDay();
      const diff = 3 - day; // Wednesday
      const wed = new Date(now);
      wed.setDate(now.getDate() + diff);
      simDateIso = wed.toISOString();
    }

    this.api.evaluateCart(items, simDateIso).subscribe({
      next: (res) => {
        this.simResult = res;
        this.evaluatingSim = false;
        this.cdr.markForCheck();
      },
      error: (err) => {
        console.error('Failed to run simulation', err);
        this.evaluatingSim = false;
        this.cdr.markForCheck();
      }
    });
  }

  setSimQty(productId: number, qty: number): void {
    if (qty <= 0) {
      delete this.simSelectedProductIds[productId];
    } else {
      this.simSelectedProductIds[productId] = qty;
    }
  }

  getSimQty(productId: number): number {
    return this.simSelectedProductIds[productId] || 0;
  }

  setActiveView(view: 'codes' | 'ai' | 'split'): void {
    this.activeView = view;
    this.cdr.markForCheck();
  }

  toggleRule(r: DiscountRule): void {
    const originalState = r.is_active;
    this.api.toggleDiscountRule(r.id).subscribe({
      next: (updated) => {
        r.is_active = updated.is_active;
        r.status = updated.status;
        r.is_expired = updated.is_expired;
        this.loadRules();
        this.cdr.markForCheck();
      },
      error: (err) => {
        console.error('Failed to toggle rule', err);
        r.is_active = originalState;
        this.cdr.markForCheck();
      }
    });
  }

  deleteRule(r: DiscountRule): void {
    if (!confirm(`Are you sure you want to delete discount rule "${r.name}" (${r.code || 'No code'})?`)) {
      return;
    }
    this.api.deleteDiscountRule(r.id).subscribe({
      next: () => {
        this.loadRules();
        this.cdr.markForCheck();
      },
      error: (err) => console.error('Failed to delete rule', err)
    });
  }

  quickRenew(r: DiscountRule, days: number): void {
    const targetDate = new Date();
    targetDate.setDate(targetDate.getDate() + days);
    const dateStr = targetDate.toISOString().split('T')[0];

    this.api.updateDiscountRule(r.id, {
      is_active: true,
      end_date: dateStr
    }).subscribe({
      next: () => {
        this.editingExpiryRuleId = null;
        this.loadRules();
        this.cdr.markForCheck();
      },
      error: (err) => console.error('Failed to quick renew rule', err)
    });
  }

  setAlwaysActive(r: DiscountRule): void {
    this.api.updateDiscountRule(r.id, {
      is_active: true,
      end_date: ''
    }).subscribe({
      next: () => {
        this.editingExpiryRuleId = null;
        this.loadRules();
        this.cdr.markForCheck();
      },
      error: (err) => console.error('Failed to set always active', err)
    });
  }

  openExpiryPicker(r: DiscountRule): void {
    if (this.editingExpiryRuleId === r.id) {
      this.editingExpiryRuleId = null;
    } else {
      this.editingExpiryRuleId = r.id;
      this.customExpiryInput = r.end_date || new Date(Date.now() + 7 * 86400000).toISOString().split('T')[0];
    }
    this.cdr.markForCheck();
  }

  saveCustomExpiry(r: DiscountRule): void {
    if (!this.customExpiryInput) return;
    this.api.updateDiscountRule(r.id, {
      is_active: true,
      end_date: this.customExpiryInput
    }).subscribe({
      next: () => {
        this.editingExpiryRuleId = null;
        this.loadRules();
        this.cdr.markForCheck();
      },
      error: (err) => console.error('Failed to save custom expiry', err)
    });
  }

  private scrollToBottom(): void {
    setTimeout(() => {
      const chatElem = document.getElementById('chat-scroll-container');
      if (chatElem) {
        chatElem.scrollTop = chatElem.scrollHeight;
      }
    }, 100);
  }
}

