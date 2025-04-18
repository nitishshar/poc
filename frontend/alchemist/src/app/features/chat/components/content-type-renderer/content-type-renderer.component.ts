import { CommonModule } from '@angular/common';
import { Component, Input, OnInit } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatTableModule } from '@angular/material/table';
import { DomSanitizer } from '@angular/platform-browser';
import { NgxChartsModule } from '@swimlane/ngx-charts';
import {
  CardData,
  ContentItem,
  GraphData,
  TableData,
} from '../../models/chat.types';

@Component({
  selector: 'app-content-type-renderer',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatTableModule, NgxChartsModule],
  template: `
    <ng-container [ngSwitch]="content.type">
      <!-- Text content -->
      <div *ngSwitchCase="'text'" class="text-content">
        {{ content.content }}
      </div>

      <!-- Image content -->
      <div *ngSwitchCase="'image'" class="image-content">
        <img [src]="content.content" alt="Image" />
      </div>

      <!-- Table content -->
      <div *ngSwitchCase="'table'" class="table-content">
        <table
          mat-table
          [dataSource]="tableDataSource"
          class="mat-elevation-z0"
        >
          <ng-container
            *ngFor="let column of getTableColumns(); let i = index"
            [matColumnDef]="column"
          >
            <th mat-header-cell *matHeaderCellDef>{{ column }}</th>
            <td mat-cell *matCellDef="let row">{{ row[i] }}</td>
          </ng-container>

          <tr mat-header-row *matHeaderRowDef="getTableColumns()"></tr>
          <tr mat-row *matRowDef="let row; columns: getTableColumns()"></tr>
        </table>
      </div>

      <!-- Card content -->
      <div *ngSwitchCase="'card'" class="card-content">
        <mat-card>
          <img
            *ngIf="getCardData().image"
            mat-card-image
            [src]="getCardData().image"
            alt="Card image"
          />
          <mat-card-header>
            <mat-card-title *ngIf="getCardData().title">
              {{ getCardData().title }}
            </mat-card-title>
            <mat-card-subtitle *ngIf="getCardData().subtitle">
              {{ getCardData().subtitle }}
            </mat-card-subtitle>
          </mat-card-header>
          <mat-card-content>
            {{ getCardData().content }}
          </mat-card-content>
        </mat-card>
      </div>

      <!-- Graph content -->
      <div *ngSwitchCase="'graph'" class="graph-content">
        <ngx-charts-bar-vertical
          *ngIf="getGraphData().type === 'bar'"
          [results]="chartData"
          [gradient]="true"
          [xAxis]="true"
          [yAxis]="true"
          [legend]="true"
          [showXAxisLabel]="true"
          [showYAxisLabel]="true"
          [xAxisLabel]="xAxisLabel"
          [yAxisLabel]="yAxisLabel"
          [scheme]="colorScheme"
        >
        </ngx-charts-bar-vertical>

        <ngx-charts-line-chart
          *ngIf="getGraphData().type === 'line'"
          [results]="chartData"
          [gradient]="false"
          [xAxis]="true"
          [yAxis]="true"
          [legend]="true"
          [showXAxisLabel]="true"
          [showYAxisLabel]="true"
          [xAxisLabel]="xAxisLabel"
          [yAxisLabel]="yAxisLabel"
          [scheme]="colorScheme"
        >
        </ngx-charts-line-chart>

        <ngx-charts-pie-chart
          *ngIf="getGraphData().type === 'pie'"
          [results]="chartData"
          [gradient]="false"
          [legend]="true"
          [labels]="true"
          [doughnut]="false"
          [scheme]="colorScheme"
        >
        </ngx-charts-pie-chart>
      </div>

      <!-- HTML content -->
      <div
        *ngSwitchCase="'html'"
        class="html-content"
        [innerHTML]="content.content"
      ></div>

      <!-- Default case -->
      <div *ngSwitchDefault class="unknown-content">
        Unsupported content type: {{ content.type }}
      </div>
    </ng-container>
  `,
  styles: [
    `
      :host {
        display: block;
        width: 100%;
      }

      .text-content {
        font-size: 14px;
        line-height: 1.5;
        word-wrap: break-word;
      }

      .image-content {
        max-width: 100%;
        overflow: hidden;
        border-radius: 4px;

        img {
          max-width: 100%;
          height: auto;
          display: block;
        }
      }

      .table-content {
        width: 100%;
        overflow-x: auto;
        background: var(--glass-card-background);
        border-radius: var(--border-radius);
        margin: 8px 0;
        border: var(--glass-border);

        table {
          width: 100%;
          color: var(--text-color);
        }

        th {
          font-weight: 500;
          color: var(--text-color);
          background: rgba(var(--primary-color-rgb), 0.1);
          padding: 12px 16px;
        }

        td {
          color: var(--text-color);
          padding: 12px 16px;
        }

        tr {
          border-bottom: var(--glass-border);
        }

        tr:last-child {
          border-bottom: none;
        }

        /* Override Material table styles */
        ::ng-deep {
          .mat-mdc-table {
            background: transparent;
          }

          .mdc-data-table__row {
            background: transparent;
          }

          .mdc-data-table__header-cell {
            color: var(--text-color);
            background: rgba(var(--primary-color-rgb), 0.1);
          }

          .mdc-data-table__cell {
            color: var(--text-color);
          }
        }
      }

      .card-content {
        width: 100%;
        margin: 8px 0;

        mat-card {
          background: rgba(255, 255, 255, 0.05) !important;
          color: var(--text-color);
          border: var(--glass-border);
        }

        img {
          max-height: 200px;
          object-fit: cover;
        }

        mat-card-title {
          color: var(--text-color);
          font-size: 16px;
        }

        mat-card-subtitle {
          color: var(--secondary-text-color);
        }

        mat-card-content {
          color: var(--text-color);
          font-size: 14px;
          line-height: 1.5;
        }
      }

      .graph-content {
        width: 95%;
        min-height: 300px;
        height:350px;
        margin: 12px 0;
        position: relative;
        background: var(--glass-card-background);
        border: var(--glass-border);
        border-radius: var(--border-radius);
        padding: 16px;

        /* Override ngx-charts text colors */
        ::ng-deep {
          .ngx-charts {
            text {
              fill: var(--text-color) !important;
            }

            .legend-title,
            .legend-label,
            .grid-line-path {
              color: var(--text-color) !important;
              stroke: var(--text-color) !important;
            }

            .legend-labels {
              background: var(--glass-card-background) !important;
            }

            .tick {
              text {
                fill: var(--text-color) !important;
              }
              line {
                stroke: var(--text-color) !important;
                opacity: 0.2;
              }
            }

            .gridline-path {
              stroke: var(--text-color) !important;
              opacity: 0.1;
            }

            .line-series .line {
              stroke-width: 2;
            }

            .tooltip-anchor {
              fill: var(--text-color);
            }
          }
        }
      }

      .html-content {
        width: 100%;
        overflow-x: auto;
      }

      /* Deep styling for HTML content */
      ::ng-deep .html-content {
        color: var(--text-color);
      }

      ::ng-deep .html-content a {
        color: var(--primary-color);
      }

      ::ng-deep .html-content pre,
      ::ng-deep .html-content code {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 4px;
        padding: 8px;
      }

      .unknown-content {
        padding: 8px;
        background-color: rgba(255, 0, 0, 0.1);
        border-radius: 4px;
        color: var(--warning-color);
        font-size: 12px;
      }

      ::ng-deep {
        .delete-icon {
          color: var(--error-color) !important;
        }

        .mat-icon-button:hover .delete-icon {
          color: var(--error-hover-color) !important;
        }
      }
    `,
  ],
})
export class ContentTypeRendererComponent implements OnInit {
  @Input() content!: ContentItem;

  // Chart configuration for ngx-charts
  chartData: any[] = [];
  xAxisLabel: string = '';
  yAxisLabel: string = '';
  colorScheme: any = {
    domain: ['#5AA454', '#A10A28', '#C7B42C', '#AAAAAA'],
  };

  // Table data source for mat-table
  tableDataSource: any[] = [];

  constructor(private sanitizer: DomSanitizer) {}

  ngOnInit(): void {
    // Process data based on content type
    switch (this.content.type) {
      case 'table':
        this.setupTableData();
        break;
      case 'graph':
        this.setupChartData();
        break;
      case 'html':
        // Ensure HTML is sanitized
        if (typeof this.content.content === 'string') {
          this.content = {
            type: 'html',
            content: this.sanitizer.bypassSecurityTrustHtml(
              this.content.content as string
            ),
          };
        }
        break;
    }
  }

  // Get table data from content
  getTableData(): TableData {
    return this.content.type === 'table'
      ? (this.content.content as TableData)
      : { columns: [], rows: [] };
  }

  // Get table columns
  getTableColumns(): string[] {
    return this.content.type === 'table' ? this.getTableData().columns : [];
  }

  // Get card data from content
  getCardData(): CardData {
    return this.content.type === 'card'
      ? (this.content.content as CardData)
      : { content: '' };
  }

  // Get graph data from content
  getGraphData(): GraphData {
    return this.content.type === 'graph'
      ? (this.content.content as GraphData)
      : {
          type: 'bar',
          labels: [],
          datasets: [],
        };
  }

  // Setup table data source for mat-table
  private setupTableData(): void {
    if (this.content.type === 'table') {
      const tableData = this.getTableData();
      this.tableDataSource = tableData.rows;
    }
  }

  // Setup chart data for ngx-charts
  private setupChartData(): void {
    if (this.content.type === 'graph') {
      const graphData = this.getGraphData();

      if (graphData.type === 'pie') {
        this.chartData = graphData.labels.map((label, index) => ({
          name: label,
          value: graphData.datasets[0].data[index],
        }));
      } else if (graphData.type === 'bar') {
        // Transform bar chart data
        this.chartData = graphData.labels.map((label, index) => ({
          name: label,
          value: graphData.datasets[0].data[index],
        }));
      } else {
        // For line charts
        this.chartData = graphData.datasets.map((dataset) => ({
          name: dataset.label,
          series: graphData.labels.map((label, index) => ({
            name: label,
            value: dataset.data[index],
          })),
        }));
      }

      // Set axis labels if provided or use defaults
      this.xAxisLabel = 'Category';
      this.yAxisLabel = 'Value';

      // Set color scheme
      if (graphData.datasets[0].backgroundColor) {
        if (Array.isArray(graphData.datasets[0].backgroundColor)) {
          this.colorScheme = {
            domain: graphData.datasets[0].backgroundColor,
          };
        } else {
          // If single color provided, create a color scheme
          this.colorScheme = {
            domain: [graphData.datasets[0].backgroundColor],
          };
        }
      }
    }
  }
}
