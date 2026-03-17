import React, { useState, useEffect, useRef } from 'react';
import { useApp } from '../context/AppContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import { toast } from 'sonner';
import {
  Wallet,
  RefreshCw,
  Settings,
  CheckCircle2,
  XCircle,
  Clock,
  Loader2,
  Link as LinkIcon,
  ExternalLink,
  AlertTriangle,
  Users,
  IndianRupee,
  Upload,
  FileJson,
  Trash2,
} from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const AdvanceManagement = () => {
  const { employees } = useApp();
  const [isConnected, setIsConnected] = useState(false);
  const [credentialsConfigured, setCredentialsConfigured] = useState(false);
  const [credentialsInfo, setCredentialsInfo] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSyncing, setIsSyncing] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [sheetConfig, setSheetConfig] = useState({
    spreadsheetId: '',
    sheetName: 'Sheet1',
    range: 'A:F',
  });
  const [advances, setAdvances] = useState([]);
  const [syncStats, setSyncStats] = useState({
    total: 0,
    matched: 0,
    pending: 0,
    errors: 0,
  });
  const [lastSync, setLastSync] = useState(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    checkCredentials();
    checkConnection();
    loadAdvances();
    loadSheetConfig();
    
    // Check URL params for connection status
    const params = new URLSearchParams(window.location.search);
    if (params.get('connected') === 'true') {
      toast.success('Google Sheets connected successfully!');
      setIsConnected(true);
      window.history.replaceState({}, '', '/advance');
    }
    if (params.get('error')) {
      toast.error(`Connection error: ${params.get('error')}`);
      window.history.replaceState({}, '', '/advance');
    }
  }, []);

  const checkCredentials = async () => {
    try {
      const res = await fetch(`${API_URL}/api/google-sheets/credentials-status`, { credentials: 'include' });
      const data = await res.json();
      setCredentialsConfigured(data.configured);
      if (data.configured) {
        setCredentialsInfo(data);
      }
    } catch (err) {
      setCredentialsConfigured(false);
    }
  };

  const checkConnection = async () => {
    try {
      const res = await fetch(`${API_URL}/api/google-sheets/status`, { credentials: 'include' });
      const data = await res.json();
      setIsConnected(data.connected);
    } catch (err) {
      setIsConnected(false);
    } finally {
      setIsLoading(false);
    }
  };

  const loadAdvances = async () => {
    try {
      const res = await fetch(`${API_URL}/api/advance/list`, { credentials: 'include' });
      if (res.ok) {
        const data = await res.json();
        setAdvances(data.advances || []);
        setSyncStats(data.stats || { total: 0, matched: 0, pending: 0, errors: 0 });
        setLastSync(data.lastSync);
      }
    } catch (err) {
      console.error('Error loading advances:', err);
    }
  };

  const loadSheetConfig = async () => {
    try {
      const res = await fetch(`${API_URL}/api/google-sheets/config`, { credentials: 'include' });
      if (res.ok) {
        const data = await res.json();
        if (data.spreadsheetId) {
          setSheetConfig(data);
        }
      }
    } catch (err) {
      console.error('Error loading config:', err);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    if (!file.name.endsWith('.json')) {
      toast.error('Please upload a JSON file');
      return;
    }
    
    setIsUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const res = await fetch(`${API_URL}/api/google-sheets/upload-credentials`, {
        method: 'POST',
        credentials: 'include',
        body: formData,
      });
      const data = await res.json();
      
      if (data.success) {
        toast.success('Credentials uploaded successfully!');
        setCredentialsConfigured(true);
        setCredentialsInfo({ client_id: data.client_id });
      } else {
        toast.error(data.detail || 'Upload failed');
      }
    } catch (err) {
      toast.error('Failed to upload credentials');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleDeleteCredentials = async () => {
    if (!window.confirm('Credentials delete करना है? Google Sheet disconnect हो जाएगा।')) return;
    try {
      await fetch(`${API_URL}/api/google-sheets/credentials`, { 
        method: 'DELETE', 
        credentials: 'include' 
      });
      setCredentialsConfigured(false);
      setCredentialsInfo(null);
      setIsConnected(false);
      toast.success('Credentials removed');
    } catch (err) {
      toast.error('Failed to remove credentials');
    }
  };

  const handleGoogleLogin = () => {
    window.location.href = `${API_URL}/api/google-sheets/login`;
  };

  const handleDisconnect = async () => {
    if (!window.confirm('Google Sheets disconnect करना है?')) return;
    try {
      await fetch(`${API_URL}/api/google-sheets/disconnect`, { method: 'POST', credentials: 'include' });
      setIsConnected(false);
      toast.success('Disconnected from Google Sheets');
    } catch (err) {
      toast.error('Failed to disconnect');
    }
  };

  const handleSaveConfig = async () => {
    if (!sheetConfig.spreadsheetId) {
      toast.error('Sheet ID required है');
      return;
    }
    try {
      const res = await fetch(`${API_URL}/api/google-sheets/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(sheetConfig),
      });
      if (res.ok) {
        toast.success('Sheet config saved!');
      } else {
        toast.error('Failed to save config');
      }
    } catch (err) {
      toast.error('Error saving config');
    }
  };

  const handleSync = async () => {
    if (!sheetConfig.spreadsheetId) {
      toast.error('Pehle Sheet ID configure karo');
      return;
    }
    setIsSyncing(true);
    try {
      const res = await fetch(`${API_URL}/api/advance/sync`, {
        method: 'POST',
        credentials: 'include',
      });
      const data = await res.json();
      if (data.success) {
        toast.success(`Sync complete! ${data.matched} entries matched, ${data.errors} errors`);
        loadAdvances();
      } else {
        toast.error(data.message || 'Sync failed');
      }
    } catch (err) {
      toast.error('Sync failed');
    } finally {
      setIsSyncing(false);
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'Done':
        return <Badge className="bg-green-500/20 text-green-600"><CheckCircle2 className="w-3 h-3 mr-1" />Done</Badge>;
      case 'Error':
        return <Badge className="bg-red-500/20 text-red-600"><XCircle className="w-3 h-3 mr-1" />Error</Badge>;
      default:
        return <Badge className="bg-yellow-500/20 text-yellow-600"><Clock className="w-3 h-3 mr-1" />Pending</Badge>;
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
            <Wallet className="w-8 h-8 text-green-500" />
            Advance Management
          </h1>
          <p className="text-muted-foreground mt-1">
            Google Sheet से Salary type के advance sync करें
          </p>
        </div>
        {isConnected && (
          <Button onClick={handleSync} disabled={isSyncing} className="gap-2" data-testid="sync-btn">
            {isSyncing ? (
              <><Loader2 className="w-4 h-4 animate-spin" /> Syncing...</>
            ) : (
              <><RefreshCw className="w-4 h-4" /> Sync Now</>
            )}
          </Button>
        )}
      </div>

      {/* Step 1: Upload Credentials */}
      <Card data-testid="credentials-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileJson className="w-5 h-5" />
            Step 1: Google OAuth Credentials
          </CardTitle>
          <CardDescription>
            Google Cloud Console से OAuth credentials JSON download करें और upload करें
          </CardDescription>
        </CardHeader>
        <CardContent>
          {!credentialsConfigured ? (
            <div className="space-y-4">
              <div className="p-4 bg-muted rounded-lg text-sm space-y-2">
                <p className="font-medium">Google Cloud Console में ये करें:</p>
                <ol className="list-decimal list-inside space-y-1 text-muted-foreground">
                  <li>Google Cloud Console जाएं → APIs & Services → Credentials</li>
                  <li>OAuth 2.0 Client ID create करें (Web application)</li>
                  <li>Redirect URI में add करें: <code className="bg-background px-1 rounded">{API_URL}/api/google-sheets/callback</code></li>
                  <li>JSON download करें और नीचे upload करें</li>
                </ol>
              </div>
              
              <div className="flex items-center gap-4">
                <input
                  type="file"
                  accept=".json"
                  onChange={handleFileUpload}
                  ref={fileInputRef}
                  className="hidden"
                  id="credentials-upload"
                />
                <Button 
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isUploading}
                  className="gap-2"
                  data-testid="upload-credentials-btn"
                >
                  {isUploading ? (
                    <><Loader2 className="w-4 h-4 animate-spin" /> Uploading...</>
                  ) : (
                    <><Upload className="w-4 h-4" /> Upload JSON</>
                  )}
                </Button>
                <a 
                  href="https://console.cloud.google.com/apis/credentials" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="text-sm text-primary hover:underline flex items-center gap-1"
                >
                  Open Google Cloud Console <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-between p-3 bg-green-500/10 rounded-lg">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-green-500" />
                <div>
                  <span className="font-medium text-green-600">Credentials Configured</span>
                  <p className="text-xs text-muted-foreground">Client ID: {credentialsInfo?.client_id}</p>
                </div>
              </div>
              <Button variant="outline" size="sm" onClick={handleDeleteCredentials} className="gap-1">
                <Trash2 className="w-3 h-3" /> Remove
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Step 2: Connect Google Account */}
      {credentialsConfigured && (
        <Card data-testid="connection-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <LinkIcon className="w-5 h-5" />
              Step 2: Google Account Connect करें
            </CardTitle>
          </CardHeader>
          <CardContent>
            {!isConnected ? (
              <div className="text-center py-6">
                <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-muted flex items-center justify-center">
                  <ExternalLink className="w-8 h-8 text-muted-foreground" />
                </div>
                <h3 className="text-lg font-medium mb-2">Google Account से Login करें</h3>
                <p className="text-muted-foreground mb-4">
                  Sheet access के लिए Google account से login करें
                </p>
                <Button onClick={handleGoogleLogin} className="gap-2" data-testid="google-login-btn">
                  <svg className="w-5 h-5" viewBox="0 0 24 24">
                    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                  </svg>
                  Connect with Google
                </Button>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="flex items-center justify-between p-3 bg-green-500/10 rounded-lg">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-5 h-5 text-green-500" />
                    <span className="font-medium text-green-600">Connected to Google Sheets</span>
                  </div>
                  <Button variant="outline" size="sm" onClick={handleDisconnect}>
                    Disconnect
                  </Button>
                </div>

                {/* Sheet Configuration */}
                <div className="grid gap-4 md:grid-cols-3">
                  <div>
                    <Label htmlFor="spreadsheetId">Spreadsheet ID *</Label>
                    <Input
                      id="spreadsheetId"
                      value={sheetConfig.spreadsheetId}
                      onChange={(e) => setSheetConfig({ ...sheetConfig, spreadsheetId: e.target.value })}
                      placeholder="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
                      data-testid="spreadsheet-id-input"
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      URL से ID copy करें: docs.google.com/spreadsheets/d/<strong>ID</strong>/edit
                    </p>
                  </div>
                  <div>
                    <Label htmlFor="sheetName">Sheet Name</Label>
                    <Input
                      id="sheetName"
                      value={sheetConfig.sheetName}
                      onChange={(e) => setSheetConfig({ ...sheetConfig, sheetName: e.target.value })}
                      placeholder="Sheet1"
                      data-testid="sheet-name-input"
                    />
                  </div>
                  <div>
                    <Label htmlFor="range">Range</Label>
                    <Input
                      id="range"
                      value={sheetConfig.range}
                      onChange={(e) => setSheetConfig({ ...sheetConfig, range: e.target.value })}
                      placeholder="A:F"
                      data-testid="range-input"
                    />
                  </div>
                </div>
                <Button onClick={handleSaveConfig} data-testid="save-config-btn">
                  <Settings className="w-4 h-4 mr-2" />
                  Save Configuration
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Sync Stats */}
      {isConnected && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4 text-center">
              <Users className="w-6 h-6 mx-auto mb-2 text-blue-500" />
              <div className="text-2xl font-bold">{syncStats.total}</div>
              <div className="text-sm text-muted-foreground">Total Entries</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <CheckCircle2 className="w-6 h-6 mx-auto mb-2 text-green-500" />
              <div className="text-2xl font-bold">{syncStats.matched}</div>
              <div className="text-sm text-muted-foreground">Matched</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <Clock className="w-6 h-6 mx-auto mb-2 text-yellow-500" />
              <div className="text-2xl font-bold">{syncStats.pending}</div>
              <div className="text-sm text-muted-foreground">Pending</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <XCircle className="w-6 h-6 mx-auto mb-2 text-red-500" />
              <div className="text-2xl font-bold">{syncStats.errors}</div>
              <div className="text-sm text-muted-foreground">Errors</div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Advance List */}
      {isConnected && advances.length > 0 && (
        <Card data-testid="advance-list-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <IndianRupee className="w-5 h-5" />
              Synced Advances (Type: Salary)
            </CardTitle>
            <CardDescription>
              Last sync: {lastSync ? new Date(lastSync).toLocaleString() : 'Never'}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Date</TableHead>
                    <TableHead>Employee Code</TableHead>
                    <TableHead>Name</TableHead>
                    <TableHead className="text-right">Amount</TableHead>
                    <TableHead className="text-center">Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {advances.map((adv, idx) => (
                    <TableRow key={idx}>
                      <TableCell>{adv.date}</TableCell>
                      <TableCell className="font-mono">{adv.employeeCode}</TableCell>
                      <TableCell>{adv.name}</TableCell>
                      <TableCell className="text-right font-mono">₹{adv.amount?.toLocaleString()}</TableCell>
                      <TableCell className="text-center">{getStatusBadge(adv.syncStatus)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Empty State */}
      {isConnected && advances.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center">
            <AlertTriangle className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
            <h3 className="text-lg font-medium mb-2">No Advances Synced</h3>
            <p className="text-muted-foreground mb-4">
              Sheet configure करें और "Sync Now" button click करें
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default AdvanceManagement;
