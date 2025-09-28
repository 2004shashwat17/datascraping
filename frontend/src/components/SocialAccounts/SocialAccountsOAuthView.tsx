import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Box,
  Card,
  CardContent,
  CardHeader,
  Typography,
  Button,
  Chip,
  Alert,
  CircularProgress,
} from '@mui/material';
import {
  Facebook,
  Instagram,
  Twitter,
  YouTube,
  Reddit,
  Refresh,
  Delete,
  OpenInBrowser,
  CheckCircle,
} from '@mui/icons-material';
import { apiClient } from '../../services/apiClient';
import type { 
  SocialAccount
} from '../../types/api';const SocialAccountsOAuthView: React.FC = () => {
  const [accounts, setAccounts] = useState<SocialAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [connecting, setConnecting] = useState<string | null>(null);
  const [disconnecting, setDisconnecting] = useState<string | null>(null);
  const [searchParams] = useSearchParams();

  const platformIcons: Record<string, React.ReactElement> = {
    facebook: <Facebook sx={{ color: '#1877F2' }} />,
    instagram: <Instagram sx={{ color: '#E4405F' }} />,
    twitter: <Twitter sx={{ color: '#1DA1F2' }} />,
    youtube: <YouTube sx={{ color: '#FF0000' }} />,
    reddit: <Reddit sx={{ color: '#FF4500' }} />,
  };

  const platformNames: Record<string, string> = {
    facebook: 'Facebook',
    instagram: 'Instagram',
    twitter: 'Twitter',
    youtube: 'YouTube',
    reddit: 'Reddit',
  };

  useEffect(() => {
    loadAccounts();
    
    // Handle OAuth callback
    const success = searchParams.get('success');
    const errorParam = searchParams.get('error');
    const platform = searchParams.get('platform');
    
    if (success === 'true' && platform) {
      // OAuth successful
      loadAccounts(); // Refresh accounts
      // Clear URL params
      window.history.replaceState({}, document.title, window.location.pathname);
    } else if (errorParam && platform) {
      // OAuth failed
      setError(`Failed to connect ${platform}: ${errorParam}`);
      // Clear URL params
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, [searchParams]);

  const loadAccounts = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await apiClient.get('/oauth/accounts');
      const accountsData = response.data as { accounts: SocialAccount[] };
      setAccounts(accountsData.accounts);

    } catch (err: any) {
      console.error('Error loading social accounts:', err);
      setError(err.response?.data?.detail || 'Failed to load social accounts');
    } finally {
      setLoading(false);
    }
  };

  const handleConnect = async (platform: string) => {
    try {
      setConnecting(platform);
      setError(null);

      const response = await apiClient.get(`/oauth/connect/${platform}`);
      const connectData = response.data as { auth_url: string; state: string };

      // Check if this is a test mode URL
      if (connectData.auth_url.includes('oauth-mock')) {
        // Simulate successful OAuth callback for testing
        console.log(`Test mode: Simulating successful OAuth for ${platform}`);
        
        // Simulate the callback by calling the backend callback endpoint with mock data
        try {
          const callbackUrl = `/${platform}/callback?code=test_code_${platform}_${Date.now()}&state=${connectData.state}`;
          await apiClient.get(callbackUrl);
          
          // Refresh accounts to show the new connection
          await loadAccounts();
          
          // Show success message
          setError(null);
          // You could add a success alert here
          
        } catch (callbackErr: any) {
          console.error(`Test mode callback failed for ${platform}:`, callbackErr);
          setError(`Test connection failed for ${platform}`);
        }
      } else {
        // Open real OAuth URL in new window
        window.open(connectData.auth_url, '_blank', 'width=600,height=700');
      }

    } catch (err: any) {
      console.error(`Error connecting to ${platform}:`, err);
      setError(err.response?.data?.detail || `Failed to connect to ${platform}`);
    } finally {
      setConnecting(null);
    }
  };

  const handleDisconnect = async (platform: string) => {
    try {
      setDisconnecting(platform);
      setError(null);

      await apiClient.delete(`/oauth/disconnect/${platform}`);
      await loadAccounts(); // Refresh accounts

    } catch (err: any) {
      console.error(`Error disconnecting ${platform}:`, err);
      setError(err.response?.data?.detail || `Failed to disconnect ${platform}`);
    } finally {
      setDisconnecting(null);
    }
  };

  const isConnected = (platform: string) => {
    return accounts.some(account => account.platform === platform);
  };

  const getAccountInfo = (platform: string) => {
    return accounts.find(account => account.platform === platform);
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ maxWidth: 1200, mx: 'auto', p: 3 }}>
      <Typography variant="h4" gutterBottom sx={{ mb: 3, fontWeight: 'bold' }}>
        Social Media Accounts
      </Typography>

      <Typography variant="body1" color="textSecondary" sx={{ mb: 4 }}>
        Connect your social media accounts to enable comprehensive data collection and analysis.
        We use OAuth 2.0 for secure authentication.
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 3 }}>
        {Object.entries(platformNames).map(([platform, name]) => {
          const connected = isConnected(platform);
          const account = getAccountInfo(platform);
          const isConnecting = connecting === platform;
          const isDisconnecting = disconnecting === platform;

          return (
            <Card key={platform} sx={{ height: '100%' }}>
              <CardHeader
                avatar={platformIcons[platform]}
                title={name}
                subheader={connected ? `Connected as ${account?.username}` : 'Not connected'}
                action={
                  connected ? (
                    <Chip
                      label="Connected"
                      color="success"
                      size="small"
                      icon={<CheckCircle />}
                    />
                  ) : null
                }
              />
              <CardContent>
                <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
                  {connected
                    ? `Last synced: ${account?.last_sync ? new Date(account.last_sync).toLocaleDateString() : 'Never'}`
                    : `Connect your ${name} account to collect posts, friends, and activity data.`
                  }
                </Typography>

                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                  {connected ? (
                    <>
                      <Button
                        variant="outlined"
                        color="primary"
                        startIcon={<Refresh />}
                        disabled={isDisconnecting}
                      >
                        Sync Data
                      </Button>
                      <Button
                        variant="outlined"
                        color="error"
                        startIcon={isDisconnecting ? <CircularProgress size={16} /> : <Delete />}
                        onClick={() => handleDisconnect(platform)}
                        disabled={isDisconnecting}
                      >
                        {isDisconnecting ? 'Disconnecting...' : 'Disconnect'}
                      </Button>
                    </>
                  ) : (
                    <Button
                      variant="contained"
                      color="primary"
                      startIcon={isConnecting ? <CircularProgress size={16} /> : <OpenInBrowser />}
                      onClick={() => handleConnect(platform)}
                      disabled={isConnecting}
                      fullWidth
                    >
                      {isConnecting ? 'Connecting...' : `Connect ${name}`}
                    </Button>
                  )}
                </Box>

                {connected && (
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="subtitle2" gutterBottom>
                      Data Collection:
                    </Typography>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {account?.collect_posts && (
                        <Chip label="Posts" size="small" color="primary" variant="outlined" />
                      )}
                      {account?.collect_connections && (
                        <Chip label="Connections" size="small" color="primary" variant="outlined" />
                      )}
                      {account?.collect_interactions && (
                        <Chip label="Interactions" size="small" color="primary" variant="outlined" />
                      )}
                    </Box>
                  </Box>
                )}
              </CardContent>
            </Card>
          );
        })}
      </Box>

      <Alert severity="info" sx={{ mt: 4 }}>
        <Typography variant="body2">
          <strong>Security Note:</strong> We use industry-standard OAuth 2.0 authentication.
          Your credentials are never stored on our servers. Data collection is performed
          according to each platform's terms of service and your configured preferences.
        </Typography>
      </Alert>
    </Box>
  );
};

export default SocialAccountsOAuthView;