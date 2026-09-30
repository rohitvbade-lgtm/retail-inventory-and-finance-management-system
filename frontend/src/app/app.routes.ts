import { Routes } from '@angular/router';
import { PosComponent } from './components/pos/pos.component';
import { InventoryComponent } from './components/inventory/inventory.component';
import { FinanceComponent } from './components/finance/finance.component';
import { DiscountsComponent } from './components/discounts/discounts.component';

export const routes: Routes = [
  { path: '', redirectTo: 'pos', pathMatch: 'full' },
  { path: 'pos', component: PosComponent },
  { path: 'inventory', component: InventoryComponent },
  { path: 'finance', component: FinanceComponent },
  { path: 'discounts', component: DiscountsComponent },
  { path: '**', redirectTo: 'pos' }
];

