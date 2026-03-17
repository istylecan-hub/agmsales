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
  Key,
  TestTube,
  Copy,
} from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const AdvanceManagement = () => {
  const { employees } = useApp();
  const [isConnected, setIsConnected] = useState(false);
  const [connectionInfo, setConnectionInfo] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSyncing, setIsSyncing] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
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
    checkConnection();
    loadAdvances();
    loadSheetConfig();
  }, []);

  const checkConnection = async () => {
    try {
      const res = await fetch(`${API_URL}/api/google-sheets/status`, { credentials: 'include' });
      const data = await res.json();
      setIsConnected(data.connected);
      if (data.connected) {
        setConnectionInfo(data);
      }
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
      const res = await fetch(`${API_URL}/api/google-sheets/upload-service-account`, {
        method: 'POST',
        credentials: 'include',
        body: formData,
      });
      const data = await res.json();
      
      if (data.success) {
        toast.success('Service Account uploaded!');
        setIsConnected(true);
        setConnectionInfo({
          client_email: data.client_email,
          project_id: data.project_id
        });
      } else {
        toast.error(data.detail || 'Upload failed');
      }
    } catch (err) {
      toast.error('Failed to upload Service Account');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleDisconnect = async () => {
    if (!window.confirm('Service Account remove करना है?')) return;
    try {
      await fetch(`${API_URL}/api/google-sheets/disconnect`, { 
        method: 'DELETE', 
        credentials: 'include' 
      });
      setIsConnected(false);
      setConnectionInfo(null);
      toast.success('Service Account removed');
    } catch (err) {
      toast.error('Failed to remove');
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

  const handleTestConnection = async () => {
    setIsTesting(true);
    try {
      const res = await fetch(`${API_URL}/api/google-sheets/test-connection`, {
        method: 'POST',
        credentials: 'include',
      });
      const data = await res.json();
      if (data.success) {
        toast.success(data.message);
      } else {
        toast.error(data.detail || 'Test failed');
      }
    } catch (err) {
      toast.error('Connection test failed');
    } finally {
      setIsTesting(false);
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
        toast.success(`Sync complete! ${data.matched} matched, ${data.errors} errors`);
        loadAdvances();
      } else {
        toast.error(data.message || data.detail || 'Sync failed');
      }
    } catch (err) {
      toast.error('Sync failed');
    } finally {
      setIsSyncing(false);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied!');
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
        {isConnected && sheetConfig.spreadsheetId && (
          <Button onClick={handleSync} disabled={isSyncing} className="gap-2" data-testid="sync-btn">
            {isSyncing ? (
              <><Loader2 className="w-4 h-4 animate-spin" /> Syncing...</>
            ) : (
              <><RefreshCw className="w-4 h-4" /> Sync Now</>
            )}
          </Button>
        )}
      </div>

      {/* Step 1: Upload Service Account */}
      <Card data-testid="service-account-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Key className="w-5 h-5" />
            Step 1: Service Account Setup
          </CardTitle>
          <CardDescription>
            Google Cloud से Service Account JSON key upload करें
          </CardDescription>
        </CardHeader>
        <CardContent>
          {!isConnected ? (
            <div className="space-y-4">
              <div className="p-4 bg-muted rounded-lg text-sm space-y-2">
                <p className="font-medium">Google Cloud Console में ये करें:</p>
                <ol className="list-decimal list-inside space-y-1 text-muted-foreground">
                  <li>Google Cloud Console → IAM & Admin → Service Accounts</li>
                  <li>Create Service Account (name: agm-sheets-reader)</li>
                  <li>Keys tab → Add Key → Create new key → JSON</li>
                  <li>JSON file download होगा, वो यहाँ upload करें</li>
                </ol>
              </div>
              
              <div className="flex items-center gap-4">
                <input
                  type="file"
                  accept=".json"
                  onChange={handleFileUpload}
                  ref={fileInputRef}
                  className="hidden"
                  id="sa-upload"
                />
                <Button 
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isUploading}
                  className="gap-2"
                  data-testid="upload-sa-btn"
                >
                  {isUploading ? (
                    <><Loader2 className="w-4 h-4 animate-spin" /> Uploading...</>
                  ) : (
                    <><Upload className="w-4 h-4" /> Upload Service Account JSON</>
                  )}
                </Button>
                <a 
                  href="https://console.cloud.google.com/iam-admin/serviceaccounts" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="text-sm text-primary hover:underline flex items-center gap-1"
                >
                  Open Google Cloud <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center justify-between p-3 bg-green-500/10 rounded-lg">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-5 h-5 text-green-500" />
                  <div>
                    <span className="font-medium text-green-600">Service Account Connected</span>
                    <p className="text-xs text-muted-foreground">{connectionInfo?.project_id}</p>
                  </div>
                </div>
                <Button variant="outline" size="sm" onClick={handleDisconnect} className="gap-1">
                  <Trash2 className="w-3 h-3" /> Remove
                </Button>
              </div>
              
              {/* Important: Share sheet with service account */}
              <div className="p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="w-5 h-5 text-yellow-600 mt-0.5" />
                  <div className="flex-1">
                    <p className="font-medium text-yellow-700">Important: Sheet Share करें</p>
                    <p className="text-sm text-muted-foreground mt-1">
                      Google Sheet को इस email से share करें (Viewer access):
                    </p>
                    <div className="flex items-center gap-2 mt-2">
                      <code className="flex-1 px-3 py-2 bg-background rounded text-sm break-all">
                        {connectionInfo?.client_email}
                      </code>
                      <Button 
                        variant="outline" 
                        size="sm"
                        onClick={() => copyToClipboard(connectionInfo?.client_email)}
                      >
                        <Copy className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Step 2: Configure Sheet */}
      {isConnected && (
        <Card data-testid="sheet-config-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Settings className="w-5 h-5" />
              Step 2: Sheet Configuration
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
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
                  URL से copy करें: /spreadsheets/d/<strong>ID</strong>/edit
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
            <div className="flex gap-2">
              <Button onClick={handleSaveConfig} data-testid="save-config-btn">
                <Settings className="w-4 h-4 mr-2" />
                Save Config
              </Button>
              <Button 
                variant="outline" 
                onClick={handleTestConnection}
                disabled={isTesting || !sheetConfig.spreadsheetId}
                data-testid="test-connection-btn"
              >
                {isTesting ? (
                  <><Loader2 className="w-4 h-4 animate-spin mr-2" /> Testing...</>
                ) : (
                  <><TestTube className="w-4 h-4 mr-2" /> Test Connection</>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Sync Stats */}
      {isConnected && sheetConfig.spreadsheetId && (
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
      {advances.length > 0 && (
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
      {isConnected && sheetConfig.spreadsheetId && advances.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center">
            <AlertTriangle className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
            <h3 className="text-lg font-medium mb-2">No Advances Synced</h3>
            <p className="text-muted-foreground mb-4">
              "Sync Now" button click करें data लाने के लिए
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default AdvanceManagement;
