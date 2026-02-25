import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../components/ui/dialog';
import { AlertCircle, Download, Search, CheckCircle, Upload } from 'lucide-react';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const OrderHubUnmappedSKUs = () => {
  const [skus, setSkus] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [showMap, setShowMap] = useState(false);
  const [selectedSku, setSelectedSku] = useState(null);
  const [masterSku, setMasterSku] = useState('');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [skusRes, summaryRes] = await Promise.all([
        fetch(`${API_URL}/api/orderhub/unmapped/list`, { credentials: 'include' }),
        fetch(`${API_URL}/api/orderhub/unmapped/summary`, { credentials: 'include' })
      ]);

      if (skusRes.ok) setSkus(await skusRes.json());
      if (summaryRes.ok) setSummary(await summaryRes.json());
    } catch (err) {
      console.error('Error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = () => {
    window.open(`${API_URL}/api/orderhub/unmapped/export`, '_blank');
  };

  const handleMap = async () => {
    if (!masterSku) {
      toast.error('Enter Master SKU');
      return;
    }

    try {
      const res = await fetch(
        `${API_URL}/api/orderhub/unmapped/map-single?sku=${encodeURIComponent(selectedSku.sku)}&master_sku=${encodeURIComponent(masterSku)}`,
        { method: 'POST', credentials: 'include' }
      );

      if (res.ok) {
        toast.success('SKU mapped successfully!');
        setShowMap(false);
        setSelectedSku(null);
        setMasterSku('');
        fetchData();
      } else {
        const data = await res.json();
        toast.error(data.detail || 'Failed to map');
      }
    } catch (err) {
      toast.error('Error mapping SKU');
    }
  };

  const handleBulkUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch(`${API_URL}/api/orderhub/unmapped/bulk-upload`, {
        method: 'POST',
        body: formData,
        credentials: 'include'
      });

      const data = await res.json();
      if (res.ok) {
        toast.success(`Processed: ${data.mappings_processed} mappings, ${data.remapped} SKUs remapped`);
        fetchData();
      } else {
        toast.error(data.detail || 'Upload failed');
      }
    } catch (err) {
      toast.error('Upload error');
    }
    e.target.value = '';
  };

  const openMapDialog = (sku) => {
    setSelectedSku(sku);
    setMasterSku(sku.suggested_master_sku || '');
    setShowMap(true);
  };

  const filteredSKUs = skus.filter(s => {
    if (!search) return true;
    return s.sku?.toLowerCase().includes(search.toLowerCase()) ||
           s.platform?.toLowerCase().includes(search.toLowerCase());
  });

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Unmapped SKUs</h1>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleExport}>
            <Download className="h-4 w-4 mr-2" /> Export CSV
          </Button>
          <Label className="cursor-pointer">
            <Input type="file" accept=".csv,.xlsx,.xls" onChange={handleBulkUpload} className="hidden" />
            <Button variant="outline" asChild>
              <span><Upload className="h-4 w-4 mr-2" /> Bulk Import</span>
            </Button>
          </Label>
        </div>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Unmapped SKUs</p>
                  <p className="text-2xl font-bold">{summary.total_unmapped_skus}</p>
                </div>
                <AlertCircle className="h-8 w-8 text-orange-500" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div>
                <p className="text-sm text-muted-foreground">Total Quantity</p>
                <p className="text-2xl font-bold">{summary.total_unmapped_qty?.toLocaleString()}</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div>
                <p className="text-sm text-muted-foreground">Revenue at Risk</p>
                <p className="text-2xl font-bold text-orange-600">₹{summary.total_unmapped_revenue?.toLocaleString()}</p>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* SKU List */}
      <Card>
        <CardHeader>
          <div className="flex justify-between items-center">
            <CardTitle>Unmapped SKU List</CardTitle>
            <div className="relative w-64">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input placeholder="Search..." value={search} onChange={(e) => setSearch(e.target.value)} className="pl-9" />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-center py-8">Loading...</p>
          ) : filteredSKUs.length === 0 ? (
            <div className="text-center py-8">
              <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-2" />
              <p className="text-muted-foreground">All SKUs are mapped!</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-muted/50">
                    <th className="text-left p-3">SKU</th>
                    <th className="text-left p-3">Platform</th>
                    <th className="text-left p-3">Qty</th>
                    <th className="text-left p-3">Revenue</th>
                    <th className="text-left p-3">Suggestion</th>
                    <th className="text-left p-3">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredSKUs.slice(0, 100).map(s => (
                    <tr key={s.id} className="border-b hover:bg-muted/30">
                      <td className="p-3 font-mono text-xs">{s.sku}</td>
                      <td className="p-3 capitalize">{s.platform}</td>
                      <td className="p-3">{s.total_qty?.toLocaleString()}</td>
                      <td className="p-3">₹{s.total_revenue?.toLocaleString()}</td>
                      <td className="p-3">
                        {s.suggested_master_sku ? (
                          <span className="text-green-600 text-xs">{s.suggested_master_sku} ({s.suggestion_confidence}%)</span>
                        ) : '-'}
                      </td>
                      <td className="p-3">
                        <Button size="sm" onClick={() => openMapDialog(s)}>Map</Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Map Dialog */}
      <Dialog open={showMap} onOpenChange={setShowMap}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Map SKU</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 mt-4">
            <div>
              <Label>SKU</Label>
              <Input value={selectedSku?.sku || ''} disabled />
            </div>
            <div>
              <Label>Platform</Label>
              <Input value={selectedSku?.platform || ''} disabled />
            </div>
            <div>
              <Label>Master SKU *</Label>
              <Input 
                value={masterSku} 
                onChange={(e) => setMasterSku(e.target.value)} 
                placeholder="e.g., 338-Maroon-S" 
              />
              {selectedSku?.suggested_master_sku && (
                <p className="text-xs text-green-600 mt-1">
                  Suggestion: {selectedSku.suggested_master_sku} ({selectedSku.suggestion_confidence}% match)
                </p>
              )}
            </div>
            <Button onClick={handleMap} className="w-full">Save Mapping</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default OrderHubUnmappedSKUs;
