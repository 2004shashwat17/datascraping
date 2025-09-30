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
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormControlLabel,
  Checkbox,
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
  Login,
} from '@mui/icons-material';
import { apiClient } from '../../services/apiClient';
import type {
  SocialAccount,
  OAuthAccountsResponse,
  OAuthConnectResponse
} from '../../types/api';

const SocialAccountsOAuthView: React.FC = () => {
  const [accounts, setAccounts] = useState<SocialAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [connecting, setConnecting] = useState<string | null>(null);
  const [disconnecting, setDisconnecting] = useState<string | null>(null);
  const [searchParams] = useSearchParams();

  // Credential form state
  const [credentialDialogOpen, setCredentialDialogOpen] = useState(false);
  const [selectedPlatform, setSelectedPlatform] = useState<string>('');
  const [credentials, setCredentials] = useState({
    email: '',
    password: '',
    target: '',
    maxPosts: 10,
    apiToken: '',
    collectOwnData: false, // New field for comprehensive collection
  });

  const platformIcons: Record<string, React.ReactElement> = {
    facebook: <Facebook sx={{ color: '#1877F2' }} />,
    instagram: <Instagram sx={{ color: '#E4405F' }} />,
    twitter: <Twitter sx={{ color: '#1DA1F2' }} />,
    youtube: <YouTube sx={{ color: '#FF0000' }} />,
    reddit: <Reddit sx={{ color: '#FF4500' }} />,
  };

  const platformNames: Record<string, string> = {
    facebook: 'Facebook',
    instagram: 'Instagram (Credential-based Scraping - Feed, Posts, Followers, Following)',
    twitter: 'Twitter',
    youtube: 'YouTube',
    reddit: 'Reddit',
  };

  const loadAccounts = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get<OAuthAccountsResponse>('/oauth/accounts');
      setAccounts(response.data.accounts || []);
    } catch (err: any) {
      console.error('Error loading accounts:', err);
      setError('Failed to load connected accounts');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAccounts();

    // Handle OAuth callback
    const success = searchParams.get('success');
    const errorParam = searchParams.get('error');
    const platform = searchParams.get('platform');

    console.log('OAuth callback detected:', { success, error: errorParam, platform, currentPath: window.location.pathname });

    if (success === 'true' && platform) {
      // OAuth successful
      console.log(`OAuth success for ${platform}, refreshing accounts...`);
      loadAccounts(); // Refresh accounts
      setSuccessMessage(`${platform.charAt(0).toUpperCase() + platform.slice(1)} connected successfully!`);
      // Clear success message after 5 seconds
      setTimeout(() => setSuccessMessage(null), 5000);
      // Clear URL params
      window.history.replaceState({}, document.title, window.location.pathname);
      console.log('URL params cleared, staying on social-accounts page');
    } else if (errorParam && platform) {
      // OAuth failed
      console.log(`OAuth error for ${platform}: ${errorParam}`);
      setError('Failed to connect');
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, [searchParams]);

  // Also check for OAuth parameters on mount in case the useEffect doesn't trigger
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const success = urlParams.get('success');
    const errorParam = urlParams.get('error');
    const platform = urlParams.get('platform');

    if (success === 'true' && platform) {
      console.log('OAuth success detected on mount for', platform);
      loadAccounts();
      setSuccessMessage(`${platform.charAt(0).toUpperCase() + platform.slice(1)} connected successfully!`);
      // Clear success message after 5 seconds
      setTimeout(() => setSuccessMessage(null), 5000);
      // Clear URL params
      window.history.replaceState({}, document.title, window.location.pathname);
    } else if (errorParam && platform) {
      console.log('OAuth error detected on mount for', platform);
      setError('Failed to connect');
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []); // Run only on mount

  const handleConnect = async (platform: string) => {
    try {
      setConnecting(platform);
      setError(null);

      // For Instagram, show credential form instead of OAuth
      if (platform === 'instagram') {
        setSelectedPlatform(platform);
        setCredentialDialogOpen(true);
        setConnecting(null);
        return;
      }

      // For other platforms, use OAuth
      // Map frontend platform names to backend API names
      const apiPlatform = platform === 'youtube' ? 'google' : platform;
      const response = await apiClient.get<OAuthConnectResponse>(`/oauth/connect/${apiPlatform}`);
      if (response.data.auth_url) {
        window.location.href = response.data.auth_url;
      }
    } catch (err: any) {
      console.error('Error connecting:', err);
      setError(err.response?.data?.detail || 'Failed to connect');
    } finally {
      setConnecting(null);
    }
  };

  const handleDisconnect = async (platform: string) => {
    try {
      setDisconnecting(platform);
      setError(null);

      // Map frontend platform names to backend API names
      const apiPlatform = platform === 'youtube' ? 'google' : platform;
      await apiClient.delete(`/oauth/disconnect/${apiPlatform}`);
      
      // Refresh accounts after disconnect
      await loadAccounts();
    } catch (err: any) {
      console.error('Error disconnecting:', err);
      setError(err.response?.data?.detail || 'Failed to disconnect');
    } finally {
      setDisconnecting(null);
    }
  };

  const handleCredentialSubmit = async () => {
    try {
      setConnecting(selectedPlatform);
      setError(null);

      const requestData = {
        platform: selectedPlatform,
        email: credentials.email,
        password: credentials.password,
        target: credentials.collectOwnData ? null : credentials.target, // Send null for comprehensive collection
        max_posts: credentials.maxPosts,
        ...(credentials.apiToken && { api_token: credentials.apiToken }),
      };

      const response = await apiClient.post('/collect/connect/credentials', requestData);

      if ((response.data as any).success) {
        setError(null);
        // Close dialog and reset form
        setCredentialDialogOpen(false);
        setCredentials({
          email: '',
          password: '',
          target: '',
          maxPosts: 10,
          apiToken: '',
          collectOwnData: false,
        });
        // Optionally refresh accounts or show success message
        loadAccounts();
      } else {
        setError((response.data as any).error || 'Failed to connect with credentials');
      }
    } catch (err: any) {
      console.error('Error connecting with credentials:', err);
      setError(err.response?.data?.detail || 'Failed to connect with credentials');
    } finally {
      setConnecting(null);
    }
  };

  const handleCredentialDialogClose = () => {
    setCredentialDialogOpen(false);
    setCredentials({
      email: '',
      password: '',
      target: '',
      maxPosts: 10,
      apiToken: '',
      collectOwnData: false,
    });
  };

  const getAccountInfo = (platform: string) => {
    return accounts.find(account => account.platform === platform);
  };

  const isConnected = (platform: string) => {
    return accounts.some(account => account.platform === platform);
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ maxWidth: 800, mx: 'auto', p: 3 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Social Media Accounts
      </Typography>

      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        Connect your social media accounts to collect and analyze data from your profiles.
        All connections use secure OAuth authentication.
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {successMessage && (
        <Alert severity="success" sx={{ mb: 3 }}>
          {successMessage}
        </Alert>
      )}

      <Box sx={{ display: 'grid', gap: 3 }}>
        {Object.entries(platformNames).map(([platform, name]) => {
          const account = getAccountInfo(platform);
          const connected = isConnected(platform);
          const isConnecting = connecting === platform;
          const isDisconnecting = disconnecting === platform;

          return (
            <Card key={platform} variant="outlined">
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    {platformIcons[platform]}
                    <Box>
                      <Typography variant="h6">{name}</Typography>
                      {connected && account ? (
                        <Box sx={{ mt: 1 }}>
                          <Chip
                            label={`Connected as ${account.username}`}
                            color="success"
                            size="small"
                            icon={<CheckCircle />}
                          />
                          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                            Last sync: {account.last_sync ? new Date(account.last_sync).toLocaleString() : 'Never'}
                          </Typography>
                        </Box>
                      ) : (
                        <Typography variant="body2" color="text.secondary">
                          Not connected
                        </Typography>
                      )}
                    </Box>
                  </Box>

                  <Box sx={{ display: 'flex', gap: 1 }}>
                    {connected ? (
                      <>
                        <Button
                          variant="outlined"
                          startIcon={<Refresh />}
                          onClick={() => loadAccounts()}
                          disabled={loading}
                        >
                          Refresh
                        </Button>
                        <Button
                          variant="outlined"
                          color="error"
                          startIcon={<Delete />}
                          onClick={() => handleDisconnect(platform)}
                          disabled={isDisconnecting}
                        >
                          {isDisconnecting ? <CircularProgress size={20} /> : 'Disconnect'}
                        </Button>
                      </>
                    ) : (
                      <Button
                        variant="contained"
                        startIcon={platform === 'instagram' ? <Login /> : <OpenInBrowser />}
                        onClick={() => handleConnect(platform)}
                        disabled={isConnecting}
                      >
                        {isConnecting ? <CircularProgress size={20} /> : 
                         platform === 'instagram' ? 'Enter Credentials' : 'Connect'}
                      </Button>
                    )}
                  </Box>
                </Box>
              </CardContent>
            </Card>
          );
        })}
      </Box>

      <Alert severity="info" sx={{ mt: 4 }}>
        <Typography variant="body2">
          <strong>Note:</strong> Instagram supports comprehensive data collection including your feed, posts, followers, and following.
          Other platforms use OAuth 2.0 for secure authentication. Your credentials are never stored on our servers.
        </Typography>
      </Alert>

      {/* Credential Input Dialog */}
      <Dialog open={credentialDialogOpen} onClose={handleCredentialDialogClose} maxWidth="sm" fullWidth>
        <DialogTitle>
          {credentials.collectOwnData ? 'Collect Your Instagram Data' : `Connect to ${platformNames[selectedPlatform] || selectedPlatform}`}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              label="Email"
              type="email"
              value={credentials.email}
              onChange={(e) => setCredentials({ ...credentials, email: e.target.value })}
              fullWidth
              required
            />
            <TextField
              label="Password"
              type="password"
              value={credentials.password}
              onChange={(e) => setCredentials({ ...credentials, password: e.target.value })}
              fullWidth
              required
            />
            {selectedPlatform === 'instagram' && (
              <FormControlLabel
                control={
                  <Checkbox
                    checked={credentials.collectOwnData}
                    onChange={(e) => setCredentials({ ...credentials, collectOwnData: e.target.checked })}
                  />
                }
                label="Collect my own comprehensive data (feed, posts, followers, following)"
              />
            )}
            {!credentials.collectOwnData && (
              <TextField
                label="Target Username/Profile"
                value={credentials.target}
                onChange={(e) => setCredentials({ ...credentials, target: e.target.value })}
                fullWidth
                required={!credentials.collectOwnData}
                helperText={credentials.collectOwnData ? "Not needed for own data collection" : "Enter the Instagram username to scrape data from"}
                disabled={credentials.collectOwnData}
              />
            )}
            <TextField
              label="Maximum Items"
              type="number"
              value={credentials.maxPosts}
              onChange={(e) => setCredentials({ ...credentials, maxPosts: parseInt(e.target.value) || 10 })}
              fullWidth
              inputProps={{ min: 1, max: 100 }}
              helperText={credentials.collectOwnData ? "Maximum posts/followers/following to collect (1-100)" : "Maximum number of posts to collect (1-100)"}
            />
            {selectedPlatform !== 'instagram' && (
              <TextField
                label="API Token (Optional)"
                value={credentials.apiToken}
                onChange={(e) => setCredentials({ ...credentials, apiToken: e.target.value })}
                fullWidth
                helperText="Apify API token for enhanced scraping"
              />
            )}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCredentialDialogClose}>Cancel</Button>
          <Button
            onClick={handleCredentialSubmit}
            variant="contained"
            disabled={connecting === selectedPlatform || !credentials.email || !credentials.password || (!credentials.collectOwnData && !credentials.target)}
            startIcon={connecting === selectedPlatform ? <CircularProgress size={20} /> : <Login />}
          >
            {connecting === selectedPlatform ? 'Connecting...' : credentials.collectOwnData ? 'Connect & Collect My Data' : 'Connect & Scrape'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default SocialAccountsOAuthView;
