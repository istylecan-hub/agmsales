import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../../components/ui/dialog';
import { Plus, Search, Trash2, Upload } from 'lucide-react';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const OrderHubMasterSKUs = () => {
  const [skus, setSkus] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [showAdd, setShowAdd] = useState(false);
  const [newSku, setNewSku] = useState({ sku: '', master_sku: '', product_name: '' });

  useEffect(() => {
    fetchSKUs();
  }, []);

  const fetchSKUs = async () => {
    try {
      const res = await fetch(`${API_URL}/api/orderhub/master-skus`, { credentials: 'include' });
      if (res.ok) setSkus(await res.json());
    } catch (err) {
      console.error('Error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAdd = async () => {
    if (!newSku.sku || !newSku.master_sku) {
      toast.error('SKU and Master SKU are required');
      return;
    }

    try {
      const res = await fetch(
        `${API_URL}/api/orderhub/master-skus?sku=${encodeURIComponent(newSku.sku)}&master_sku=${encodeURIComponent(newSku.master_sku)}&product_name=${encodeURIComponent(newSku.product_name || '')}`,
        { method: 'POST', credentials: 'include' }
      );

      if (res.ok) {
        toast.success('SKU added');
        setShowAdd(false);
        setNewSku({ sku: '', master_sku: '', product_name: '' });
        fetchSKUs();
      } else {
        const data = await res.json();
        toast.error(data.detail || 'Failed to add');
      }
    } catch (err) {
      toast.error('Error adding SKU');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this SKU mapping?')) return;

    try {
      const res = await fetch(`${API_URL}/api/orderhub/master-skus/${id}`, {
        method: 'DELETE',
        credentials: 'include'
      });

      if (res.ok) {
        toast.success('Deleted');
        fetchSKUs();
      } else {
        toast.error('Failed to delete');
      }
    } catch (err) {
      toast.error('Error deleting');
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch(`${API_URL}/api/orderhub/upload/master-sku`, {
        method: 'POST',
        body: formData,
        credentials: 'include'
      });

      const data = await res.json();
      if (res.ok) {
        toast.success(`Uploaded: ${data.inserted} new, ${data.updated} updated`);
        fetchSKUs();
      } else {
        toast.error(data.detail || 'Upload failed');
      }
    } catch (err) {
      toast.error('Upload error');
    }
    e.target.value = '';
  };

  const filteredSKUs = skus.filter(s => {
    if (!search) return true;
    const searchLower = search.toLowerCase();
    return s.sku?.toLowerCase().includes(searchLower) || 
           s.master_sku?.toLowerCase().includes(searchLower) ||
           s.product_name?.toLowerCase().includes(searchLower);
  });

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Master SKUs</h1>
        <div className="flex gap-2">
          <Label className="cursor-pointer">
            <Input type="file" accept=".csv,.xlsx,.xls" onChange={handleFileUpload} className="hidden" />
            <Button variant="outline" asChild>
              <span><Upload className="h-4 w-4 mr-2" /> Import CSV</span>
            </Button>
          </Label>
          <Dialog open={showAdd} onOpenChange={setShowAdd}>
            <DialogTrigger asChild>
              <Button><Plus className="h-4 w-4 mr-2" /> Add SKU</Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Add Master SKU</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 mt-4">
                <div>
                  <Label>SKU *</Label>
                  <Input value={newSku.sku} onChange={(e) => setNewSku({...newSku, sku: e.target.value})} placeholder="Seller SKU" />
                </div>
                <div>
                  <Label>Master SKU *</Label>
                  <Input value={newSku.master_sku} onChange={(e) => setNewSku({...newSku, master_sku: e.target.value})} placeholder="e.g., 338-Maroon-S" />
                </div>
                <div>
                  <Label>Product Name</Label>
                  <Input value={newSku.product_name} onChange={(e) => setNewSku({...newSku, product_name: e.target.value})} placeholder="Optional" />
                </div>
                <Button onClick={handleAdd} className="w-full">Add Mapping</Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      <Card>
        <CardHeader>
          <div className="flex justify-between items-center">
            <CardTitle>{filteredSKUs.length} SKU Mappings</CardTitle>
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
            <p className="text-center py-8 text-muted-foreground">No SKU mappings found</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-muted/50">
                    <th className="text-left p-3">SKU</th>
                    <th className="text-left p-3">Master SKU</th>
                    <th className="text-left p-3">Product Name</th>
                    <th className="text-left p-3">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredSKUs.slice(0, 100).map(s => (
                    <tr key={s.id} className="border-b hover:bg-muted/30">
                      <td className="p-3 font-mono text-xs">{s.sku}</td>
                      <td className="p-3 font-medium">{s.master_sku}</td>
                      <td className="p-3">{s.product_name || '-'}</td>
                      <td className="p-3">
                        <Button variant="ghost" size="sm" onClick={() => handleDelete(s.id)}>
                          <Trash2 className="h-4 w-4 text-red-500" />
                        </Button>
                      </td>
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

export default OrderHubMasterSKUs;
