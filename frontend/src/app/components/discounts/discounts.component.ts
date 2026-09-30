import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
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
  styleUrls: ['./discounts.component.css']
})
export class DiscountsComponent implements OnInit {
  chatMessages: ChatMessage[] = [];
  promptInput: string = '';
  apiKey: string = '';
  showApiKeyInput: boolean = false;
  sendingMessage: boolean = false;

  rules: DiscountRule[] = [];
  loadingRules: boolean = false;

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

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    const savedKey = localStorage.getItem('gemini_api_key');
    if (savedKey) this.apiKey = savedKey;

    this.loadRules();
    this.loadChatHistory();
    this.loadProductsForSimulator();
  }

  loadRules(): void {
    this.loadingRules = true;
    this.api.getDiscountRules(false).subscribe({
      next: (data) => {
        this.rules = data;
        this.loadingRules = false;
      },
      error: (err) => {
        console.error('Failed to load rules', err);
        this.loadingRules = false;
      }
    });
  }

  loadChatHistory(): void {
    this.api.getChatHistory().subscribe({
      next: (msgs) => {
        this.chatMessages = msgs;
        this.scrollToBottom();
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
    // Add user message to UI right away
    this.chatMessages.push({
      role: 'user',
      content: text
    });
    this.promptInput = '';
    this.scrollToBottom();

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
      },
      error: (err) => {
        this.chatMessages.push({
          role: 'assistant',
          content: 'Sorry, I encountered an error processing that instruction. Please try again.'
        });
        this.sendingMessage = false;
        this.scrollToBottom();
      }
    });
  }

  toggleRule(rule: DiscountRule): void {
    this.api.toggleDiscountRule(rule.id).subscribe({
      next: (updated) => {
        rule.is_active = updated.is_active;
      },
      error: (err) => console.error('Failed to toggle rule', err)
    });
  }

  deleteRule(rule: DiscountRule): void {
    if (confirm(`Delete rule '${rule.name}'?`)) {
      this.api.deleteDiscountRule(rule.id).subscribe({
        next: () => this.loadRules(),
        error: (err) => console.error('Failed to delete rule', err)
      });
    }
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
      },
      error: (err) => {
        console.error('Failed to run simulation', err);
        this.evaluatingSim = false;
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

  private scrollToBottom(): void {
    setTimeout(() => {
      const chatElem = document.getElementById('chat-scroll-container');
      if (chatElem) {
        chatElem.scrollTop = chatElem.scrollHeight;
      }
    }, 100);
  }
}

