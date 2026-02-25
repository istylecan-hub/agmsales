import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { Download, Search } from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const OrderHubReports = () => {
  const [activeTab, setActiveTab] = useState('sku');
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');

  useEffect(() => {
    fetchReport(activeTab);
  }, [activeTab]);

  const fetchReport = async (type) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/orderhub/reports/${type}`, { credentials: 'include' });
      if (res.ok) setData(await res.json());
    } catch (err) {
      console.error('Error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = () => {
    window.open(`${API_URL}/api/orderhub/export/consolidated`, '_blank');
  };

  const filteredData = data.filter(item => {
    if (!search) return true;
    const searchLower = search.toLowerCase();
    return Object.values(item).some(val => 
      String(val).toLowerCase().includes(searchLower)
    );
  });

  const renderTable = () => {
    if (loading) return <p className="text-center py-8">Loading...</p>;
    if (filteredData.length === 0) return <p className="text-center py-8 text-muted-foreground">No data found</p>;

    const columns = Object.keys(filteredData[0] || {});
    
    return (
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/50">
              {columns.map(col => (
                <th key={col} className="text-left p-3 font-medium capitalize">
                  {col.replace(/_/g, ' ')}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filteredData.slice(0, 100).map((row, i) => (
              <tr key={i} className="border-b hover:bg-muted/30">
                {columns.map(col => (
                  <td key={col} className="p-3">
                    {typeof row[col] === 'number' 
                      ? row[col].toLocaleString() 
                      : Array.isArray(row[col]) 
                        ? row[col].join(', ') 
                        : row[col]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        {filteredData.length > 100 && (
          <p className="text-center py-2 text-sm text-muted-foreground">
            Showing 100 of {filteredData.length} records
          </p>
        )}
      </div>
    );
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Reports</h1>
        <Button onClick={handleExport} variant="outline">
          <Download className="h-4 w-4 mr-2" /> Export CSV
        </Button>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row justify-between gap-4">
            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <TabsList>
                <TabsTrigger value="sku">By SKU</TabsTrigger>
                <TabsTrigger value="master-sku">By Master SKU</TabsTrigger>
                <TabsTrigger value="platform">By Platform</TabsTrigger>
                <TabsTrigger value="state">By State</TabsTrigger>
                <TabsTrigger value="date-trend">Trends</TabsTrigger>
              </TabsList>
            </Tabs>
            <div className="relative w-full sm:w-64">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input 
                placeholder="Search..." 
                value={search} 
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {renderTable()}
        </CardContent>
      </Card>
    </div>
  );
};

export default OrderHubReports;
