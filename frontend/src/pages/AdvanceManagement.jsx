import React, { useState, useEffect, useRef } from 'react';
import { useApp } from '../context/AppContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
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
  Upload,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Loader2,
  IndianRupee,
  FileSpreadsheet,
  Trash2,
  Download,
  RefreshCw,
  Info,
} from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const AdvanceManagement = () => {
  const { employees } = useApp();
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [advances, setAdvances] = useState([]);
  const [stats, setStats] = useState({ total: 0, totalAmount: 0 });
  const [lastUpload, setLastUpload] = useState(null);
  const [uploadResult, setUploadResult] = useState(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    loadAdvances();
  }, []);

  const loadAdvances = async () => {
    setIsLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/advance/list`, { credentials: 'include' });
      if (res.ok) {
        const data = await res.json();
        setAdvances(data.advances || []);
        setStats(data.stats || { total: 0, totalAmount: 0 });
        setLastUpload(data.lastUpload);
      }
    } catch (err) {
      console.error('Error loading advances:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    const validExts = ['.csv', '.xlsx', '.xls'];
    const ext = file.name.toLowerCase().substring(file.name.lastIndexOf('.'));
    
    if (!validExts.includes(ext)) {
      toast.error('Only CSV and Excel files are supported');
      return;
    }
    
    setIsUploading(true);
    setUploadResult(null);
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const res = await fetch(`${API_URL}/api/advance/upload`, {
        method: 'POST',
        credentials: 'include',
        body: formData,
      });
      
      const data = await res.json();
      console.log('Upload response:', data);
      
      if (res.ok && data.success) {
        toast.success(`Upload complete! ${data.matched} inserted, ${data.updated} updated, ${data.errors} errors`);
        setUploadResult(data);
        loadAdvances();
      } else {
        toast.error(data.detail || 'Upload failed');
        setUploadResult({ success: false, message: data.detail });
      }
    } catch (err) {
      console.error('Upload error:', err);
      toast.error(`Upload error: ${err.message}`);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleClearAll = async () => {
    if (!window.confirm('⚠️ सभी Advance records delete करना है?\n\nयह action undo नहीं होगा।')) return;
    
    try {
      const res = await fetch(`${API_URL}/api/advance/clear`, {
        method: 'DELETE',
        credentials: 'include',
      });
      if (res.ok) {
        toast.success('All advances cleared');
        loadAdvances();
        setUploadResult(null);
      }
    } catch (err) {
      toast.error('Failed to clear advances');
    }
  };

  const downloadSampleCSV = () => {
    const sampleData = `Date,Name,Advance,No,Type,UID
15/03/2026,Ramesh Kumar,5000,001,Salary,ADV001
16/03/2026,Suresh Singh,3000,002,Salary,ADV002
17/03/2026,Amit Sharma,2500,003,Stitching,ADV003
18/03/2026,Vijay Verma,4000,004,Salary,ADV004`;
    
    const blob = new Blob([sampleData], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'advance_sample.csv';
    a.click();
    window.URL.revokeObjectURL(url);
    toast.success('Sample CSV downloaded');
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
            CSV/Excel file से Salary type के advance upload करें
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={loadAdvances} className="gap-2">
            <RefreshCw className="w-4 h-4" /> Refresh
          </Button>
          {advances.length > 0 && (
            <Button variant="destructive" onClick={handleClearAll} className="gap-2">
              <Trash2 className="w-4 h-4" /> Clear All
            </Button>
          )}
        </div>
      </div>

      {/* Upload Card */}
      <Card data-testid="upload-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Upload className="w-5 h-5" />
            Upload Advance Data
          </CardTitle>
          <CardDescription>
            CSV या Excel file upload करें (Type = "Salary" वाली entries ही process होंगी)
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Format Info */}
          <div className="p-4 bg-muted rounded-lg">
            <div className="flex items-start gap-2">
              <Info className="w-5 h-5 text-blue-500 mt-0.5" />
              <div className="text-sm space-y-2">
                <p className="font-medium">Required Columns:</p>
                <ul className="list-disc list-inside text-muted-foreground space-y-1">
                  <li><strong>Date</strong> - Transaction date</li>
                  <li><strong>Name</strong> - Employee name (must match Employee Master)</li>
                  <li><strong>Advance</strong> - Amount</li>
                  <li><strong>No</strong> - Employee Code (must match Employee Master)</li>
                  <li><strong>Type</strong> - Only "Salary" type will be processed</li>
                  <li><strong>UID</strong> - Unique ID for update/insert (optional)</li>
                </ul>
                <p className="text-yellow-600 font-medium mt-2">
                  ⚠️ Name और Employee Code दोनों match होने चाहिए
                </p>
              </div>
            </div>
          </div>

          {/* Upload Buttons */}
          <div className="flex flex-wrap items-center gap-4">
            <input
              type="file"
              accept=".csv,.xlsx,.xls"
              onChange={handleFileUpload}
              ref={fileInputRef}
              className="hidden"
              id="advance-upload"
            />
            <Button 
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
              className="gap-2"
              data-testid="upload-btn"
            >
              {isUploading ? (
                <><Loader2 className="w-4 h-4 animate-spin" /> Uploading...</>
              ) : (
                <><FileSpreadsheet className="w-4 h-4" /> Upload CSV/Excel</>
              )}
            </Button>
            <Button variant="outline" onClick={downloadSampleCSV} className="gap-2">
              <Download className="w-4 h-4" /> Download Sample CSV
            </Button>
          </div>

          {/* Upload Result */}
          {uploadResult && (
            <div className={`p-4 rounded-lg ${uploadResult.success ? 'bg-green-500/10 border border-green-500/30' : 'bg-red-500/10 border border-red-500/30'}`}>
              <div className="flex items-start gap-2">
                {uploadResult.success ? (
                  <CheckCircle2 className="w-5 h-5 text-green-500 mt-0.5" />
                ) : (
                  <XCircle className="w-5 h-5 text-red-500 mt-0.5" />
                )}
                <div className="flex-1">
                  <p className="font-medium">{uploadResult.success ? 'Upload Successful!' : 'Upload Failed'}</p>
                  {uploadResult.success && (
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-2">
                      <div className="text-center p-2 bg-background rounded">
                        <div className="text-lg font-bold text-green-600">{uploadResult.matched}</div>
                        <div className="text-xs text-muted-foreground">Inserted</div>
                      </div>
                      <div className="text-center p-2 bg-background rounded">
                        <div className="text-lg font-bold text-blue-600">{uploadResult.updated}</div>
                        <div className="text-xs text-muted-foreground">Updated</div>
                      </div>
                      <div className="text-center p-2 bg-background rounded">
                        <div className="text-lg font-bold text-yellow-600">{uploadResult.skipped}</div>
                        <div className="text-xs text-muted-foreground">Skipped</div>
                      </div>
                      <div className="text-center p-2 bg-background rounded">
                        <div className="text-lg font-bold text-red-600">{uploadResult.errors}</div>
                        <div className="text-xs text-muted-foreground">Errors</div>
                      </div>
                    </div>
                  )}
                  {uploadResult.details && uploadResult.details.length > 0 && (
                    <details className="mt-3">
                      <summary className="cursor-pointer text-sm text-muted-foreground hover:text-foreground">
                        View Details ({uploadResult.details.length} rows)
                      </summary>
                      <div className="mt-2 max-h-48 overflow-y-auto text-xs space-y-1">
                        {uploadResult.details.map((d, i) => (
                          <div key={i} className={`p-1 rounded ${
                            d.status === 'inserted' ? 'bg-green-500/10' :
                            d.status === 'updated' ? 'bg-blue-500/10' :
                            d.status === 'error' ? 'bg-red-500/10' : 'bg-yellow-500/10'
                          }`}>
                            Row {d.row}: {d.status} {d.reason && `- ${d.reason}`}
                          </div>
                        ))}
                      </div>
                    </details>
                  )}
                  {!uploadResult.success && uploadResult.message && (
                    <p className="text-sm text-red-600 mt-1">{uploadResult.message}</p>
                  )}
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="p-4 text-center">
            <FileSpreadsheet className="w-6 h-6 mx-auto mb-2 text-blue-500" />
            <div className="text-2xl font-bold">{stats.total}</div>
            <div className="text-sm text-muted-foreground">Total Records</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <IndianRupee className="w-6 h-6 mx-auto mb-2 text-green-500" />
            <div className="text-2xl font-bold">₹{stats.totalAmount?.toLocaleString()}</div>
            <div className="text-sm text-muted-foreground">Total Amount</div>
          </CardContent>
        </Card>
        <Card className="col-span-2 md:col-span-1">
          <CardContent className="p-4 text-center">
            <Upload className="w-6 h-6 mx-auto mb-2 text-purple-500" />
            <div className="text-sm font-medium">
              {lastUpload ? new Date(lastUpload).toLocaleString() : 'Never'}
            </div>
            <div className="text-sm text-muted-foreground">Last Upload</div>
          </CardContent>
        </Card>
      </div>

      {/* Advance List */}
      {advances.length > 0 && (
        <Card data-testid="advance-list-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <IndianRupee className="w-5 h-5" />
              Uploaded Advances (Type: Salary)
            </CardTitle>
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
                    <TableHead>UID</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {advances.slice(0, 50).map((adv, idx) => (
                    <TableRow key={idx}>
                      <TableCell>{adv.date}</TableCell>
                      <TableCell className="font-mono">{adv.employeeCode}</TableCell>
                      <TableCell>{adv.name}</TableCell>
                      <TableCell className="text-right font-mono">₹{adv.amount?.toLocaleString()}</TableCell>
                      <TableCell className="text-muted-foreground text-xs">{adv.uid || '-'}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              {advances.length > 50 && (
                <p className="text-center text-sm text-muted-foreground mt-4">
                  Showing 50 of {advances.length} records
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Empty State */}
      {advances.length === 0 && !uploadResult && (
        <Card>
          <CardContent className="py-12 text-center">
            <AlertTriangle className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
            <h3 className="text-lg font-medium mb-2">No Advances Uploaded</h3>
            <p className="text-muted-foreground mb-4">
              CSV या Excel file upload करें advance data लाने के लिए
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default AdvanceManagement;
