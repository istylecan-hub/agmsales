import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { 
  Trash2, 
  RefreshCw, 
  AlertTriangle, 
  Database, 
  FileX2, 
  Tags, 
  ShoppingCart,
  Loader2,
  CheckCircle2,
  XCircle
} from 'lucide-react';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const OrderHubAdmin = () => {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(null);
  const [confirmDialog, setConfirmDialog] = useState(null);

  useEffect(() => {
    fetchDataSummary();
  }, []);

  const fetchDataSummary = async () => {
    try {
      const res = await fetch(`${API_URL}/api/orderhub/admin/data-summary`, { credentials: 'include' });
      if (res.ok) {
        setSummary(await res.json());
      }
    } catch (err) {
      console.error('Error:', err);
      toast.error('Failed to load data summary');
    } finally {
      setLoading(false);
    }
  };

  // Generic API call handler
  const executeAction = async (endpoint, method = 'POST', confirmParam = 'confirm=true') => {
    setActionLoading(endpoint);
    try {
      const url = `${API_URL}/api/orderhub/admin/${endpoint}?${confirmParam}`;
      const res = await fetch(url, { 
        method, 
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' }
      });
      const data = await res.json();
      
      if (data.status === 'success') {
        toast.success(data.message || 'Action completed successfully');
        fetchDataSummary(); // Refresh data
      } else if (data.warning) {
        // This shouldn't happen since we pass confirm=true
        toast.error('Confirmation required');
      } else {
        toast.error(data.detail || 'Action failed');
      }
    } catch (err) {
      console.error('Error:', err);
      toast.error('Failed to execute action');
    } finally {
      setActionLoading(null);
      setConfirmDialog(null);
    }
  };

  const handleResetOrders = () => {
    setConfirmDialog({
      title: 'Reset All Order Data',
      description: 'This will permanently delete ALL orders, uploads, and unmapped SKUs. Master SKUs will be preserved. This action cannot be undone!',
      action: () => executeAction('reset-orders'),
      type: 'danger'
    });
  };

  const handleResetMaster = () => {
    setConfirmDialog({
      title: 'Reset Master SKU Mappings',
      description: 'This will delete ALL Master SKU mappings. All orders will become UNMAPPED and need to be re-mapped. This action cannot be undone!',
      action: () => executeAction('reset-master'),
      type: 'danger'
    });
  };

  const handleResetAll = () => {
    setConfirmDialog({
      title: 'COMPLETE RESET - Delete Everything',
      description: 'This will permanently delete ALL OrderHub data including orders, uploads, master SKUs, and unmapped SKUs. Only use this for a fresh start. THIS CANNOT BE UNDONE!',
      action: () => executeAction('reset-all', 'DELETE', 'confirm=CONFIRM_DELETE_ALL'),
      type: 'critical'
    });
  };

  const handleRemapUnmapped = async () => {
    setActionLoading('remap');
    try {
      const res = await fetch(`${API_URL}/api/orderhub/admin/remap-unmapped`, {
        method: 'POST',
        credentials: 'include'
      });
      const data = await res.json();
      toast.success(`Remapped ${data.remapped_count || 0} SKUs`);
      fetchDataSummary();
    } catch (err) {
      toast.error('Failed to remap SKUs');
    } finally {
      setActionLoading(null);
    }
  };

  const handleDeleteFile = (fileId, filename) => {
    setConfirmDialog({
      title: `Delete Upload: ${filename}`,
      description: 'This will delete this upload and all associated orders. This action cannot be undone!',
      action: () => executeAction(`delete-upload/${fileId}`),
      type: 'warning'
    });
  };

  // Confirmation Dialog Component
  const ConfirmDialog = () => {
    if (!confirmDialog) return null;
    
    const bgColor = {
      danger: 'bg-red-500 hover:bg-red-600',
      warning: 'bg-orange-500 hover:bg-orange-600',
      critical: 'bg-red-700 hover:bg-red-800'
    }[confirmDialog.type] || 'bg-red-500 hover:bg-red-600';

    return (
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4" data-testid="confirm-dialog-overlay">
        <div className="bg-card rounded-lg shadow-xl max-w-md w-full p-6 border" data-testid="confirm-dialog">
          <div className="flex items-center gap-3 mb-4">
            <AlertTriangle className={`h-6 w-6 ${confirmDialog.type === 'critical' ? 'text-red-600' : 'text-orange-500'}`} />
            <h3 className="text-lg font-semibold">{confirmDialog.title}</h3>
          </div>
          <p className="text-muted-foreground mb-6">{confirmDialog.description}</p>
          <div className="flex gap-3 justify-end">
            <Button 
              variant="outline" 
              onClick={() => setConfirmDialog(null)}
              data-testid="confirm-cancel-btn"
            >
              Cancel
            </Button>
            <Button 
              className={bgColor}
              onClick={confirmDialog.action}
              disabled={actionLoading}
              data-testid="confirm-action-btn"
            >
              {actionLoading ? (
                <><Loader2 className="h-4 w-4 animate-spin mr-2" /> Processing...</>
              ) : (
                'Confirm Delete'
              )}
            </Button>
          </div>
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold mb-6">OrderHub Admin</h1>
        <div className="grid gap-4">
          {[1,2,3].map(i => (
            <Card key={i} className="animate-pulse">
              <CardContent className="p-6"><div className="h-24 bg-muted rounded"></div></CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold" data-testid="admin-page-title">OrderHub Admin</h1>
          <p className="text-muted-foreground">Data Management & Reset Controls</p>
        </div>
        <Button variant="outline" onClick={fetchDataSummary} data-testid="refresh-summary-btn">
          <RefreshCw className="h-4 w-4 mr-2" /> Refresh
        </Button>
      </div>

      {/* Data Summary */}
      <Card data-testid="data-summary-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="h-5 w-5" /> Current Data Summary
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-4 bg-secondary rounded-lg text-center" data-testid="stat-orders">
              <ShoppingCart className="h-6 w-6 mx-auto mb-2 text-blue-500" />
              <div className="text-2xl font-bold">{summary?.total_orders?.toLocaleString() || 0}</div>
              <div className="text-sm text-muted-foreground">Total Orders</div>
            </div>
            <div className="p-4 bg-secondary rounded-lg text-center" data-testid="stat-files">
              <FileX2 className="h-6 w-6 mx-auto mb-2 text-green-500" />
              <div className="text-2xl font-bold">{summary?.total_files || 0}</div>
              <div className="text-sm text-muted-foreground">Uploaded Files</div>
            </div>
            <div className="p-4 bg-secondary rounded-lg text-center" data-testid="stat-master">
              <Tags className="h-6 w-6 mx-auto mb-2 text-purple-500" />
              <div className="text-2xl font-bold">{summary?.master_skus || 0}</div>
              <div className="text-sm text-muted-foreground">Master SKUs</div>
            </div>
            <div className="p-4 bg-secondary rounded-lg text-center" data-testid="stat-unmapped">
              <AlertTriangle className="h-6 w-6 mx-auto mb-2 text-orange-500" />
              <div className="text-2xl font-bold">{summary?.unmapped_skus || 0}</div>
              <div className="text-sm text-muted-foreground">Unmapped SKUs</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <Card data-testid="quick-actions-card">
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
          <CardDescription>Maintenance and utility operations</CardDescription>
        </CardHeader>
        <CardContent>
          <Button 
            variant="outline" 
            onClick={handleRemapUnmapped}
            disabled={actionLoading === 'remap'}
            data-testid="remap-unmapped-btn"
          >
            {actionLoading === 'remap' ? (
              <><Loader2 className="h-4 w-4 animate-spin mr-2" /> Remapping...</>
            ) : (
              <><RefreshCw className="h-4 w-4 mr-2" /> Remap Unmapped SKUs</>
            )}
          </Button>
        </CardContent>
      </Card>

      {/* Reset Controls */}
      <Card className="border-orange-500/50" data-testid="reset-controls-card">
        <CardHeader>
          <CardTitle className="text-orange-600 flex items-center gap-2">
            <AlertTriangle className="h-5 w-5" /> Reset Controls
          </CardTitle>
          <CardDescription>
            Warning: These actions are irreversible. Other modules (Invoice Extractor, Salary) are NOT affected.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Reset Orders */}
          <div className="flex items-center justify-between p-4 bg-secondary rounded-lg">
            <div>
              <h4 className="font-medium">Reset Order Data</h4>
              <p className="text-sm text-muted-foreground">
                Delete all orders, uploads, and unmapped SKUs. Master SKUs preserved.
              </p>
            </div>
            <Button 
              variant="destructive" 
              onClick={handleResetOrders}
              disabled={!!actionLoading}
              data-testid="reset-orders-btn"
            >
              <Trash2 className="h-4 w-4 mr-2" /> Reset Orders
            </Button>
          </div>

          {/* Reset Master SKUs */}
          <div className="flex items-center justify-between p-4 bg-secondary rounded-lg">
            <div>
              <h4 className="font-medium">Reset Master SKUs</h4>
              <p className="text-sm text-muted-foreground">
                Delete all master SKU mappings. All orders become unmapped.
              </p>
            </div>
            <Button 
              variant="destructive" 
              onClick={handleResetMaster}
              disabled={!!actionLoading}
              data-testid="reset-master-btn"
            >
              <Tags className="h-4 w-4 mr-2" /> Reset Master
            </Button>
          </div>

          {/* Complete Reset */}
          <div className="flex items-center justify-between p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
            <div>
              <h4 className="font-medium text-red-600">Complete Reset (Nuclear Option)</h4>
              <p className="text-sm text-muted-foreground">
                Delete ALL OrderHub data. Use only for fresh start.
              </p>
            </div>
            <Button 
              className="bg-red-700 hover:bg-red-800"
              onClick={handleResetAll}
              disabled={!!actionLoading}
              data-testid="reset-all-btn"
            >
              <AlertTriangle className="h-4 w-4 mr-2" /> Delete Everything
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Uploaded Files Management */}
      {summary?.files && summary.files.length > 0 && (
        <Card data-testid="files-management-card">
          <CardHeader>
            <CardTitle>Uploaded Files</CardTitle>
            <CardDescription>Delete individual uploads and their associated orders</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {summary.files.map((file) => (
                <div 
                  key={file.id} 
                  className="flex items-center justify-between p-3 bg-secondary rounded-lg"
                  data-testid={`file-item-${file.id}`}
                >
                  <div className="flex-1 min-w-0">
                    <div className="font-medium truncate">{file.original_filename}</div>
                    <div className="text-sm text-muted-foreground">
                      {file.platform} • {file.rows_inserted?.toLocaleString() || 0} orders • 
                      {file.created_at ? new Date(file.created_at).toLocaleDateString() : 'N/A'}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 ml-4">
                    <span className={`px-2 py-1 text-xs rounded ${
                      file.status === 'completed' ? 'bg-green-500/20 text-green-600' :
                      file.status === 'failed' ? 'bg-red-500/20 text-red-600' :
                      'bg-yellow-500/20 text-yellow-600'
                    }`}>
                      {file.status || 'unknown'}
                    </span>
                    <Button 
                      variant="ghost" 
                      size="sm"
                      className="text-red-500 hover:text-red-600 hover:bg-red-500/10"
                      onClick={() => handleDeleteFile(file.id, file.original_filename)}
                      data-testid={`delete-file-${file.id}`}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Confirmation Dialog */}
      <ConfirmDialog />
    </div>
  );
};

export default OrderHubAdmin;
