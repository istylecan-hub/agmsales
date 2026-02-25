import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Package, TrendingUp, AlertCircle, FileUp, DollarSign, ShoppingCart } from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const OrderHubDashboard = () => {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSummary();
  }, []);

  const fetchSummary = async () => {
    try {
      const res = await fetch(`${API_URL}/api/orderhub/dashboard/enterprise-summary`, { credentials: 'include' });
      if (res.ok) {
        setSummary(await res.json());
      }
    } catch (err) {
      console.error('Error:', err);
    } finally {
      setLoading(false);
    }
  };

  const StatCard = ({ title, value, subtitle, icon: Icon, trend }) => (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {subtitle && <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>}
        {trend !== undefined && (
          <p className={`text-xs mt-1 ${trend >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {trend >= 0 ? '↑' : '↓'} {Math.abs(trend)}% vs last week
          </p>
        )}
      </CardContent>
    </Card>
  );

  if (loading) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold mb-6">OrderHub Dashboard</h1>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1,2,3,4].map(i => (
            <Card key={i} className="animate-pulse">
              <CardContent className="p-6"><div className="h-16 bg-muted rounded"></div></CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">OrderHub Dashboard</h1>
        <span className="text-sm text-muted-foreground">Multi-Platform Order Analytics</span>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Orders"
          value={summary?.total_orders?.toLocaleString() || 0}
          subtitle={`Today: ${summary?.today_orders || 0}`}
          icon={ShoppingCart}
        />
        <StatCard
          title="Total Revenue"
          value={`₹${(summary?.total_revenue || 0).toLocaleString()}`}
          subtitle={`Today: ₹${(summary?.today_revenue || 0).toLocaleString()}`}
          icon={DollarSign}
          trend={summary?.growth_7_days_percent}
        />
        <StatCard
          title="Avg Order Value"
          value={`₹${summary?.avg_order_value || 0}`}
          subtitle="Per order average"
          icon={TrendingUp}
        />
        <StatCard
          title="Unmapped SKUs"
          value={summary?.unmapped_sku_count || 0}
          subtitle="Need mapping"
          icon={AlertCircle}
        />
      </div>

      {/* Projected Sales */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Projected Monthly Sales</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-green-600">
              ₹{(summary?.projected_monthly_sales || 0).toLocaleString()}
            </div>
            <p className="text-sm text-muted-foreground mt-2">Based on current month performance</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Top Performers</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {summary?.top_selling_sku && (
              <div className="flex justify-between items-center">
                <span className="text-sm">Top SKU: <strong>{summary.top_selling_sku.sku}</strong></span>
                <span className="text-sm text-green-600">₹{summary.top_selling_sku.revenue?.toLocaleString()}</span>
              </div>
            )}
            {summary?.top_platform && (
              <div className="flex justify-between items-center">
                <span className="text-sm">Top Platform: <strong>{summary.top_platform.platform}</strong></span>
                <span className="text-sm text-green-600">₹{summary.top_platform.revenue?.toLocaleString()}</span>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Quick Actions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-3">
            <a href="/orderhub/upload" className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90">
              <FileUp className="h-4 w-4" /> Upload Orders
            </a>
            <a href="/orderhub/reports" className="inline-flex items-center gap-2 px-4 py-2 bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/90">
              <TrendingUp className="h-4 w-4" /> View Reports
            </a>
            <a href="/orderhub/unmapped" className="inline-flex items-center gap-2 px-4 py-2 bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/90">
              <AlertCircle className="h-4 w-4" /> Fix Unmapped ({summary?.unmapped_sku_count || 0})
            </a>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default OrderHubDashboard;
