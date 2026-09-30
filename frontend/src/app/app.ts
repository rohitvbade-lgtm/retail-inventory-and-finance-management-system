import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { ApiService } from './services/api.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './app.html',
  styleUrls: ['./app.css']
})
export class App implements OnInit, OnDestroy {
  lowStockCount: number = 0;
  private intervalId: any;

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.refreshAlerts();
    // Poll alerts every 15 seconds to keep owner updated
    this.intervalId = setInterval(() => this.refreshAlerts(), 15000);
  }

  ngOnDestroy(): void {
    if (this.intervalId) {
      clearInterval(this.intervalId);
    }
  }

  refreshAlerts(): void {
    this.api.getLowStockAlerts().subscribe({
      next: (alerts) => (this.lowStockCount = alerts.length),
      error: () => {}
    });
  }
}

