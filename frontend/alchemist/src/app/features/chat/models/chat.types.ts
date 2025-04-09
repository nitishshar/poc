import { SafeHtml } from '@angular/platform-browser';

export interface TableData {
  columns: string[];
  rows: any[][];
}

export interface CardData {
  title?: string;
  subtitle?: string;
  content: string;
  image?: string;
}

export interface GraphData {
  type: 'line' | 'bar' | 'pie' | string;
  labels: string[];
  datasets: {
    label: string;
    data: number[];
    backgroundColor?: string[] | string;
    borderColor?: string;
  }[];
}

export type ContentType =
  | 'text'
  | 'image'
  | 'table'
  | 'card'
  | 'graph'
  | 'html';

export type ContentItem =
  | {
      type: 'text';
      content: string;
    }
  | {
      type: 'image';
      content: string; // URL
    }
  | {
      type: 'html';
      content: SafeHtml;
    }
  | {
      type: 'table';
      content: TableData;
    }
  | {
      type: 'card';
      content: CardData;
    }
  | {
      type: 'graph';
      content: GraphData;
    };

export interface ChatMessage {
  content: string;
  contentItems?: ContentItem[];
  isUser: boolean;
  timestamp: Date;
}

export interface ChatSession {
  id: string;
  created: Date;
  messages: ChatMessage[];
  lastMessageTime?: Date;
  title?: string; // Optional title for backward compatibility
}

export interface ChatState {
  sessions: ChatSession[];
  currentSession: ChatSession | null;
  isLoading: boolean;
}

// Example interface for chat suggestions
export interface ChatExample {
  text: string;
  description?: string;
  contentItems?: ContentItem[];
}

export type ContentTypeGuards = {
  isCardContent: (content: any) => content is CardData;
  isTableContent: (content: any) => content is TableData;
  isGraphContent: (content: any) => content is GraphData;
};

// Example content items for demos
export const EXAMPLE_CONTENT: Record<string, ContentItem> = {
  table: {
    type: 'table',
    content: {
      columns: ['Name', 'Value', 'Change'],
      rows: [
        ['Item 1', '100', '+10%'],
        ['Item 2', '200', '-5%'],
        ['Item 3', '150', '+2%']
      ]
    }
  },
  card: {
    type: 'card',
    content: {
      title: 'Sample Card',
      subtitle: 'With some details',
      content: 'This is a card component with formatted content.',
      image: 'https://source.unsplash.com/random/300x200?nature'
    }
  },
  barChart: {
    type: 'graph',
    content: {
      type: 'bar',
      labels: ['January', 'February', 'March', 'April'],
      datasets: [{
        label: 'Sample Data',
        data: [65, 59, 80, 81],
        backgroundColor: ['rgba(255, 99, 132, 0.7)', 'rgba(54, 162, 235, 0.7)', 'rgba(255, 206, 86, 0.7)', 'rgba(75, 192, 192, 0.7)'],
        borderColor: 'rgba(54, 162, 235, 1)'
      }]
    }
  },
  lineChart: {
    type: 'graph',
    content: {
      type: 'line',
      labels: ['January', 'February', 'March', 'April', 'May'],
      datasets: [{
        label: 'Sales',
        data: [25, 35, 50, 45, 60],
        backgroundColor: 'rgba(75, 192, 192, 0.2)',
        borderColor: 'rgba(75, 192, 192, 1)'
      }]
    }
  },
  pieChart: {
    type: 'graph',
    content: {
      type: 'pie',
      labels: ['Red', 'Blue', 'Yellow', 'Green'],
      datasets: [{
        label: 'Dataset 1',
        data: [30, 50, 20, 40],
        backgroundColor: [
          'rgba(255, 99, 132, 0.7)',
          'rgba(54, 162, 235, 0.7)',
          'rgba(255, 206, 86, 0.7)',
          'rgba(75, 192, 192, 0.7)'
        ]
      }]
    }
  }
};

// Sample chat examples
export const CHAT_EXAMPLES: ChatExample[] = [
  {
    text: 'Show me a data table example',
    description: 'Displays a table with sample data'
  },
  {
    text: 'Can you create a bar chart?',
    description: 'Generates a bar chart with sample data'
  },
  {
    text: 'I need to see a line graph',
    description: 'Creates a line chart showing data trends'
  },
  {
    text: 'Show me a pie chart example',
    description: 'Displays data as a pie chart'
  },
  {
    text: 'Show me a summary card',
    description: 'Creates a card with image and text'
  },
  {
    text: 'What kinds of rich content can you display?',
    description: 'Shows all supported content types'
  }
];
