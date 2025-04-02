import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, of, throwError } from 'rxjs';
import { ApiService } from './api.service';

interface User {
  id: string;
  username: string;
  email: string;
  is_active: boolean;
  is_superuser: boolean;
}

interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  private currentUserSubject = new BehaviorSubject<User | null>(null);
  public currentUser$ = this.currentUserSubject.asObservable();
  private isAuthenticatedSubject = new BehaviorSubject<boolean>(false);
  public isAuthenticated$ = this.isAuthenticatedSubject.asObservable();

  constructor(private apiService: ApiService) {
    this.loadUserFromStorage();
  }

  private loadUserFromStorage(): void {
    const token = localStorage.getItem('auth_token');
    const userStr = localStorage.getItem('current_user');

    if (token && userStr) {
      try {
        const user = JSON.parse(userStr);
        this.currentUserSubject.next(user);
        this.isAuthenticatedSubject.next(true);
      } catch (error) {
        console.error('Error parsing user from storage', error);
        this.logout();
      }
    }
  }

  login(username: string, password: string): Observable<User> {
    // For demo purposes, simulate authentication
    // In a real app, replace with actual API call:
    // return this.apiService.post<AuthResponse>('/auth/login', { username, password })

    const mockUser: User = {
      id: '1',
      username: username,
      email: `${username}@example.com`,
      is_active: true,
      is_superuser: username === 'admin',
    };

    const mockToken = 'mock_jwt_token_' + Math.random().toString(36).substr(2);

    localStorage.setItem('auth_token', mockToken);
    localStorage.setItem('current_user', JSON.stringify(mockUser));

    this.currentUserSubject.next(mockUser);
    this.isAuthenticatedSubject.next(true);

    return of(mockUser);
  }

  logout(): void {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('current_user');
    this.currentUserSubject.next(null);
    this.isAuthenticatedSubject.next(false);
  }

  getCurrentUser(): User | null {
    return this.currentUserSubject.value;
  }

  isAuthenticated(): boolean {
    return this.isAuthenticatedSubject.value;
  }

  // For future implementation with real backend
  register(userData: Partial<User>): Observable<User> {
    // return this.apiService.post<User>('/auth/register', userData);
    return throwError(() => new Error('Registration not implemented'));
  }
}
