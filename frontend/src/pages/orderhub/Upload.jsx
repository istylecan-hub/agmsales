import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Upload, FileUp, CheckCircle, XCircle, Clock, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const OrderHubUpload = () => {
  const [platforms, setPlatforms] = useState([]);
  const [uploads, setUploads] = useState([]);
  const [selectedPlatform, setSelectedPlatform] = useState('');
  const [account, setAccount] = useState('');
  const [uploading, setUploading] = useState(false);
  const [uploadType, setUploadType] = useState('orders');

  useEffect(() => {
    fetchPlatforms();
    fetchUploads();
  }, []);

  const fetchPlatforms = async () => {
    try {
      const res = await fetch(`${API_URL}/api/orderhub/platforms`, { credentials: 'include' });
      if (res.ok) setPlatforms(await res.json());
    } catch (err) {
      console.error('Error:', err);
    }
  };

  const fetchUploads = async () => {
    try {
      const res = await fetch(`${API_URL}/api/orderhub/upload/list`, { credentials: 'include' });
      if (res.ok) setUploads(await res.json());
    } catch (err) {
      console.error('Error:', err);
    }
  };

  const handleUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (uploadType === 'orders' && !selectedPlatform) {
      toast.error('Please select a platform');
      return;
    }

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      let url = uploadType === 'orders' 
        ? `${API_URL}/api/orderhub/upload/orders?platform=${selectedPlatform}&account=${account}`
        : `${API_URL}/api/orderhub/upload/master-sku`;

      const res = await fetch(url, {
        method: 'POST',
        body: formData,
        credentials: 'include'
      });

      const data = await res.json();
      if (res.ok) {
        toast.success(data.message || 'Upload successful!');
        fetchUploads();
      } else {
        toast.error(data.detail || 'Upload failed');
      }
    } catch (err) {
      toast.error('Upload error');
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed': return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'failed': return <XCircle className="h-4 w-4 text-red-500" />;
      case 'processing': return <RefreshCw className="h-4 w-4 text-blue-500 animate-spin" />;
      default: return <Clock className="h-4 w-4 text-yellow-500" />;
    }
  };

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Upload Orders</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Order Upload */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileUp className="h-5 w-5" /> Upload Order File
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label>Platform *</Label>
              <Select value={selectedPlatform} onValueChange={setSelectedPlatform}>
                <SelectTrigger><SelectValue placeholder="Select platform" /></SelectTrigger>
                <SelectContent>
                  {platforms.map(p => (
                    <SelectItem key={p.code} value={p.code}>{p.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Account (Optional)</Label>
              <Input value={account} onChange={(e) => setAccount(e.target.value)} placeholder="e.g., Store1" />
            </div>
            <div>
              <Label>Order File (CSV/Excel)</Label>
              <Input type="file" accept=".csv,.xlsx,.xls" onChange={(e) => { setUploadType('orders'); handleUpload(e); }} disabled={uploading} />
            </div>
            {uploading && <p className="text-sm text-muted-foreground">Uploading...</p>}
          </CardContent>
        </Card>

        {/* Master SKU Upload */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Upload className="h-5 w-5" /> Upload Master SKU
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Upload SKU mapping file with columns: <code>sku</code>, <code>master_sku</code>
            </p>
            <div>
              <Label>Master SKU File (CSV/Excel)</Label>
              <Input type="file" accept=".csv,.xlsx,.xls" onChange={(e) => { setUploadType('master'); handleUpload(e); }} disabled={uploading} />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Upload History */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Upload History</CardTitle>
          <Button variant="outline" size="sm" onClick={fetchUploads}>
            <RefreshCw className="h-4 w-4 mr-1" /> Refresh
          </Button>
        </CardHeader>
        <CardContent>
          {uploads.length === 0 ? (
            <p className="text-muted-foreground text-center py-4">No uploads yet</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="text-left p-2">File</th>
                    <th className="text-left p-2">Platform</th>
                    <th className="text-left p-2">Status</th>
                    <th className="text-left p-2">Rows</th>
                    <th className="text-left p-2">Date</th>
                  </tr>
                </thead>
                <tbody>
                  {uploads.map(u => (
                    <tr key={u.id} className="border-b hover:bg-muted/50">
                      <td className="p-2">{u.original_filename}</td>
                      <td className="p-2 capitalize">{u.platform}</td>
                      <td className="p-2 flex items-center gap-1">{getStatusIcon(u.status)} {u.status}</td>
                      <td className="p-2">{u.rows_inserted || 0} / {u.total_rows || '?'}</td>
                      <td className="p-2">{new Date(u.created_at).toLocaleDateString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default OrderHubUpload;
