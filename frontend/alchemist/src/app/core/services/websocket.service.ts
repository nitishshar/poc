import { Injectable } from '@angular/core';
import { Observable, Subject, throwError } from 'rxjs';
import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root',
})
export class WebsocketService {
  private socket: WebSocket | null = null;
  private messageSubject = new Subject<any>();
  private connectionStatusSubject = new Subject<boolean>();

  constructor() {}

  public connect(path: string): Observable<boolean> {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      return throwError(
        () => new Error('WebSocket connection already established.')
      );
    }

    const url = `${environment.websocketUrl}${path}`;
    this.socket = new WebSocket(url);

    this.socket.onopen = () => {
      console.log('WebSocket connection established.');
      this.connectionStatusSubject.next(true);
    };

    this.socket.onclose = (event) => {
      console.log(`WebSocket connection closed: ${event.code} ${event.reason}`);
      this.connectionStatusSubject.next(false);
      this.socket = null;
    };

    this.socket.onerror = (error) => {
      console.error('WebSocket error:', error);
      this.connectionStatusSubject.next(false);
    };

    this.socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.messageSubject.next(data);
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

    return this.connectionStatus();
  }

  public disconnect(): void {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.close();
      this.socket = null;
    }
  }

  public send(data: any): void {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(data));
    } else {
      throw new Error('WebSocket connection not established.');
    }
  }

  public messages(): Observable<any> {
    return this.messageSubject.asObservable();
  }

  public connectionStatus(): Observable<boolean> {
    return this.connectionStatusSubject.asObservable();
  }

  public isConnected(): boolean {
    return this.socket !== null && this.socket.readyState === WebSocket.OPEN;
  }
}
