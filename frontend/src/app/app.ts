import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { Subscription } from 'rxjs';
import { ApiService } from './services/api.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './app.html',
  styleUrls: ['./app.css'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class App implements OnInit, OnDestroy {
  lowStockCount: number = 0;
  private intervalId: any;
  private alertSub?: Subscription;

  constructor(
    private api: ApiService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.refreshAlerts();
    // Reactive alert updates from any part of the app
    this.alertSub = this.api.alertsUpdated$.subscribe(() => {
      this.refreshAlerts();
    });
    // Moderate background poll every 30 seconds
    this.intervalId = setInterval(() => this.refreshAlerts(), 30000);
  }

  ngOnDestroy(): void {
    if (this.intervalId) {
      clearInterval(this.intervalId);
    }
    if (this.alertSub) {
      this.alertSub.unsubscribe();
    }
  }

  refreshAlerts(): void {
    this.api.getLowStockAlerts().subscribe({
      next: (alerts) => {
        this.lowStockCount = alerts.length;
        this.cdr.markForCheck();
      },
      error: () => {}
    });
  }
}

