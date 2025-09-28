// TypeScript interfaces for API responses

export interface ApiResponse<T = any> {
  success: boolean;
  message?: string;
  data?: T;
}

export interface SeleniumSocialAccount {
  platform: string;
  username: string;
  connected_at: string;
  profile_data: Record<string, any>;
  posts_collected: number;
  connections_collected?: number;
  status: 'connected' | 'disconnected' | 'error';
}

export interface SocialAccount {
  id: string;
  user_id: string;
  platform: string;
  platform_user_id: string;
  username: string;
  display_name?: string;
  email?: string;
  profile_url?: string;
  profile_picture?: string;
  connected_at: string;
  last_sync?: string;
  is_active: boolean;
  collect_posts: boolean;
  collect_connections: boolean;
  collect_interactions: boolean;
}

export interface SocialPlatform {
  name: string;
  description: string;
  data_types: string[];
  features: string[];
}

export interface CollectionStats {
  total_accounts: number;
  total_posts: number;
  total_connections: number;
  total_interactions: number;
  platforms: Record<string, {
    posts: number;
    connections: number;
    interactions: number;
  }>;
}

export interface BrowserConnectionResponse {
  success: boolean;
  status: string;
  instructions?: string[];
  message?: string;
}

export interface PlatformsResponse {
  platforms: Record<string, SocialPlatform>;
}

export interface AccountsResponse {
  accounts: SeleniumSocialAccount[];
}

export interface DataCollectionResponse {
  success: boolean;
  collection_id: string;
  status: string;
  message?: string;
}

export interface SyncResponse {
  success: boolean;
  sync_types: string[];
  message?: string;
}