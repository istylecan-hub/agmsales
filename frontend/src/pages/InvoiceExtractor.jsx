import React, { useState, useCallback, useRef, useEffect } from "react";
import axios from "axios";
import { 
  Upload, 
  FileText, 
  Download, 
  Trash2, 
  Play, 
  CheckCircle, 
  XCircle, 
  Clock, 
  Loader2,
  FileSpreadsheet,
  Info,
  Eye,
  ChevronDown,
  ChevronUp,
  Building2,
  Receipt
} from "lucide-react";
import { Button } from "../components/ui/button";
import { Progress } from "../components/ui/progress";
import { Badge } from "../components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import { toast } from "sonner";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "../components/ui/tooltip";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "../components/ui/collapsible";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "../components/ui/tabs";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api/invoice`;

const InvoiceExtractor = () => {
  const [files, setFiles] = useState([]);
  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState("idle");
  const [totalFiles, setTotalFiles] = useState(0);
  const [processedFiles, setProcessedFiles] = useState(0);
  const [failedFiles, setFailedFiles] = useState(0);
  const [isDragActive, setIsDragActive] = useState(false);
  const [showInstructions, setShowInstructions] = useState(true);
  const [showDataView, setShowDataView] = useState(false);
  const [extractedData, setExtractedData] = useState([]);
  const [expandedInvoices, setExpandedInvoices] = useState({});
  const fileInputRef = useRef(null);
  const pollIntervalRef = useRef(null);

  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragActive(false);
    
    const droppedFiles = Array.from(e.dataTransfer.files).filter(
      file => file.type === "application/pdf" || file.name.toLowerCase().endsWith('.pdf')
    );
    
    if (droppedFiles.length === 0) {
      toast.error("Please drop PDF files only");
      return;
    }
    
    const validFiles = droppedFiles.filter(file => {
      if (file.size > 25 * 1024 * 1024) {
        toast.error(`${file.name} exceeds 25MB limit`);
        return false;
      }
      return true;
    });
    
    setFiles(prev => [
      ...prev, 
      ...validFiles.map(file => ({
        file,
        name: file.name,
        size: file.size,
        status: "pending",
        id: Math.random().toString(36).substr(2, 9)
      }))
    ]);
    
    if (validFiles.length > 0) {
      toast.success(`Added ${validFiles.length} file(s)`);
    }
  }, []);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setIsDragActive(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    setIsDragActive(false);
  }, []);

  const handleFileSelect = useCallback((e) => {
    const selectedFiles = Array.from(e.target.files).filter(
      file => file.type === "application/pdf" || file.name.toLowerCase().endsWith('.pdf')
    );
    
    const validFiles = selectedFiles.filter(file => {
      if (file.size > 25 * 1024 * 1024) {
        toast.error(`${file.name} exceeds 25MB limit`);
        return false;
      }
      return true;
    });
    
    setFiles(prev => [
      ...prev, 
      ...validFiles.map(file => ({
        file,
        name: file.name,
        size: file.size,
        status: "pending",
        id: Math.random().toString(36).substr(2, 9)
      }))
    ]);
    
    if (validFiles.length > 0) {
      toast.success(`Added ${validFiles.length} file(s)`);
    }
    
    e.target.value = "";
  }, []);

  const removeFile = useCallback((fileId) => {
    setFiles(prev => prev.filter(f => f.id !== fileId));
  }, []);

  const handleStartExtraction = async () => {
    if (files.length === 0) {
      toast.error("Please add PDF files first");
      return;
    }

    setJobStatus("uploading");
    setShowDataView(false);
    setExtractedData([]);
    
    try {
      const formData = new FormData();
      files.forEach(f => {
        formData.append("files", f.file);
      });

      const uploadResponse = await axios.post(`${API}/upload`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      const { job_id, files: uploadedFiles } = uploadResponse.data;
      setJobId(job_id);
      setTotalFiles(uploadedFiles.length);
      setProcessedFiles(0);
      setFailedFiles(0);

      setFiles(prev => prev.map((f, idx) => ({
        ...f,
        id: uploadedFiles[idx]?.id || f.id,
        status: "pending"
      })));

      await axios.post(`${API}/extract/${job_id}`);
      setJobStatus("processing");
      toast.success("Extraction started!");

      pollIntervalRef.current = setInterval(async () => {
        try {
          const statusResponse = await axios.get(`${API}/job/${job_id}`);
          const { status, processed_files, failed_files, files: fileStatuses } = statusResponse.data;
          
          setProcessedFiles(processed_files);
          setFailedFiles(failed_files);

          setFiles(prev => prev.map(f => {
            const updatedFile = fileStatuses.find(fs => fs.filename === f.name);
            if (updatedFile) {
              return {
                ...f,
                status: updatedFile.status,
                error: updatedFile.error_message,
                extractionData: updatedFile.extraction_data
              };
            }
            return f;
          }));

          const extracted = fileStatuses
            .filter(f => f.status === 'done' && f.extraction_data)
            .map(f => f.extraction_data);
          setExtractedData(extracted);

          if (status === "completed") {
            clearInterval(pollIntervalRef.current);
            setJobStatus("completed");
            toast.success("Extraction completed!");
          }
        } catch (error) {
          console.error("Polling error:", error);
        }
      }, 2000);

    } catch (error) {
      console.error("Upload error:", error);
      toast.error(error.response?.data?.detail || "Upload failed");
      setJobStatus("idle");
    }
  };

  const handleReset = async () => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
    }

    if (jobId) {
      try {
        await axios.delete(`${API}/job/${jobId}`);
      } catch (error) {
        console.error("Failed to delete job:", error);
      }
    }

    setFiles([]);
    setJobId(null);
    setJobStatus("idle");
    setTotalFiles(0);
    setProcessedFiles(0);
    setFailedFiles(0);
    setShowDataView(false);
    setExtractedData([]);
    setExpandedInvoices({});
    toast.success("All cleared!");
  };

  const formatSize = (bytes) => {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  };

  const formatAmount = (amount) => {
    if (amount === null || amount === undefined) return "-";
    return `₹${Number(amount).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const getTaxType = (data) => {
    if (data.igst_amount && data.igst_amount > 0) {
      return { type: "IGST", color: "bg-blue-100 text-blue-700 border-blue-200" };
    } else if ((data.cgst_amount && data.cgst_amount > 0) || (data.sgst_amount && data.sgst_amount > 0)) {
      return { type: "CGST + SGST", color: "bg-emerald-100 text-emerald-700 border-emerald-200" };
    }
    return { type: "N/A", color: "bg-stone-100 text-stone-600 border-stone-200" };
  };

  const toggleInvoiceExpand = (index) => {
    setExpandedInvoices(prev => ({
      ...prev,
      [index]: !prev[index]
    }));
  };

  const getStatusBadge = (status, error) => {
    switch (status) {
      case "pending":
        return (
          <Badge className="bg-stone-50 text-stone-500 border border-stone-200 hover:bg-stone-50">
            <Clock className="w-3 h-3 mr-1" /> Pending
          </Badge>
        );
      case "processing":
        return (
          <Badge className="bg-amber-50 text-amber-700 border border-amber-200 hover:bg-amber-50 animate-pulse">
            <Loader2 className="w-3 h-3 mr-1 animate-spin" /> Processing
          </Badge>
        );
      case "done":
        return (
          <Badge className="bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-50">
            <CheckCircle className="w-3 h-3 mr-1" /> Done
          </Badge>
        );
      case "failed":
        return (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger>
                <Badge className="bg-red-50 text-red-700 border border-red-200 hover:bg-red-50">
                  <XCircle className="w-3 h-3 mr-1" /> Failed
                </Badge>
              </TooltipTrigger>
              <TooltipContent>
                <p className="max-w-xs text-sm">{error || "Extraction failed"}</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        );
      default:
        return null;
    }
  };

  const groupedByProvider = extractedData.reduce((acc, invoice) => {
    const provider = invoice.service_provider_name || 'Unknown Provider';
    if (!acc[provider]) {
      acc[provider] = [];
    }
    acc[provider].push(invoice);
    return acc;
  }, {});

  const progress = totalFiles > 0 ? (processedFiles / totalFiles) * 100 : 0;
  const isProcessing = jobStatus === "processing" || jobStatus === "uploading";
  const isCompleted = jobStatus === "completed";

  return (
    <div className="space-y-6" data-testid="invoice-extractor-page">
      {/* Header */}
      <div>
        <h1 className="text-4xl font-bold tracking-tight font-[Manrope]">Invoice Extractor</h1>
        <p className="text-muted-foreground mt-1">
          Extract structured data from PDF invoices (Amazon, Meesho, Fashnear)
        </p>
      </div>

      {/* How to Use */}
      <Collapsible open={showInstructions} onOpenChange={setShowInstructions}>
        <CollapsibleTrigger asChild>
          <Button variant="ghost" className="flex items-center gap-2 mb-2" data-testid="how-to-use-toggle">
            <Info className="w-4 h-4" />
            <span className="font-medium">How to Use</span>
            {showInstructions ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <Card>
            <CardContent className="pt-4">
              <ol className="space-y-2 text-sm">
                <li className="flex gap-3">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-primary text-primary-foreground text-sm flex items-center justify-center font-medium">1</span>
                  <span><strong>Upload PDFs:</strong> Drag & drop or click to select invoice PDFs (max 25MB each)</span>
                </li>
                <li className="flex gap-3">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-primary text-primary-foreground text-sm flex items-center justify-center font-medium">2</span>
                  <span><strong>Start Extraction:</strong> Click the button to process all files using AI</span>
                </li>
                <li className="flex gap-3">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-primary text-primary-foreground text-sm flex items-center justify-center font-medium">3</span>
                  <span><strong>View & Download:</strong> Preview extracted data or download as CSV/Excel</span>
                </li>
              </ol>
            </CardContent>
          </Card>
        </CollapsibleContent>
      </Collapsible>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column - Upload & File List */}
        <div className="lg:col-span-8 space-y-6">
          {/* Upload Zone */}
          <Card>
            <CardContent className="p-0">
              <div
                data-testid="upload-zone"
                className={`relative h-48 border-2 border-dashed rounded-lg m-4 flex flex-col items-center justify-center cursor-pointer transition-all duration-300 ${
                  isDragActive 
                    ? "border-primary bg-primary/5" 
                    : "border-border hover:border-primary/50 hover:bg-secondary/50"
                } ${isProcessing ? "pointer-events-none opacity-60" : ""}`}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onClick={() => !isProcessing && fileInputRef.current?.click()}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept=".pdf,application/pdf"
                  className="hidden"
                  onChange={handleFileSelect}
                  data-testid="file-input"
                />
                
                <div className="flex flex-col items-center">
                  <div className="w-14 h-14 rounded-full bg-primary/10 flex items-center justify-center mb-3">
                    <Upload className="w-7 h-7 text-primary" />
                  </div>
                  <h3 className="text-lg font-semibold mb-1">Drop Invoice PDFs Here</h3>
                  <p className="text-sm text-muted-foreground">Bulk upload supported. Max 25MB per file.</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* File List */}
          {files.length > 0 && (
            <Card data-testid="file-list">
              <CardHeader className="pb-3">
                <div className="flex justify-between items-center">
                  <CardTitle className="text-lg">Files ({files.length})</CardTitle>
                  {!isProcessing && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setFiles([])}
                      className="text-destructive hover:text-destructive"
                      data-testid="clear-files-btn"
                    >
                      Clear All
                    </Button>
                  )}
                </div>
              </CardHeader>
              <CardContent className="pt-0">
                <div className="max-h-60 overflow-y-auto space-y-2">
                  {files.map((file) => (
                    <div
                      key={file.id}
                      className="flex items-center justify-between p-3 bg-secondary/30 rounded-lg"
                      data-testid={`file-item-${file.id}`}
                    >
                      <div className="flex items-center gap-3 min-w-0 flex-1">
                        <FileText className="w-5 h-5 text-orange-500 flex-shrink-0" />
                        <div className="min-w-0">
                          <p className="font-medium truncate">{file.name}</p>
                          <p className="text-xs text-muted-foreground">{formatSize(file.size)}</p>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-3">
                        {getStatusBadge(file.status, file.error)}
                        {!isProcessing && file.status === "pending" && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => removeFile(file.id)}
                            className="text-muted-foreground hover:text-destructive p-1 h-auto"
                            data-testid={`remove-file-${file.id}`}
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Extracted Data View */}
          {isCompleted && extractedData.length > 0 && showDataView && (
            <Card data-testid="data-view">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Eye className="w-5 h-5" />
                  Extracted Invoice Data
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Tabs defaultValue="by-provider" className="w-full">
                  <TabsList className="mb-4">
                    <TabsTrigger value="by-provider">
                      <Building2 className="w-4 h-4 mr-2" />
                      By Provider
                    </TabsTrigger>
                    <TabsTrigger value="all-invoices">
                      <Receipt className="w-4 h-4 mr-2" />
                      All Invoices
                    </TabsTrigger>
                  </TabsList>

                  <TabsContent value="by-provider" className="space-y-4">
                    {Object.entries(groupedByProvider).map(([provider, invoices], providerIdx) => (
                      <Card key={providerIdx} className="border-primary/20">
                        <CardHeader className="bg-primary text-primary-foreground rounded-t-lg py-3">
                          <div className="flex items-center justify-between">
                            <div>
                              <CardTitle className="text-base">{provider}</CardTitle>
                              <CardDescription className="text-primary-foreground/80">
                                {invoices.length} Invoice(s) | GSTIN: {invoices[0]?.service_provider_gstin || 'N/A'}
                              </CardDescription>
                            </div>
                            <Badge variant="secondary">{invoices[0]?.source_platform || 'Unknown'}</Badge>
                          </div>
                        </CardHeader>
                        <CardContent className="p-0">
                          {invoices.map((invoice, invIdx) => {
                            const taxType = getTaxType(invoice);
                            const invoiceKey = `${providerIdx}-${invIdx}`;
                            const isExpanded = expandedInvoices[invoiceKey];
                            
                            return (
                              <div key={invIdx} className="border-b last:border-0">
                                <div 
                                  className="p-4 cursor-pointer hover:bg-secondary/50 transition-colors"
                                  onClick={() => toggleInvoiceExpand(invoiceKey)}
                                >
                                  <div className="flex items-center justify-between">
                                    <div>
                                      <p className="font-semibold">{invoice.invoice_number || 'No Invoice #'}</p>
                                      <p className="text-sm text-muted-foreground">
                                        {invoice.invoice_date || 'No Date'} | {invoice.document_type}
                                      </p>
                                    </div>
                                    <div className="flex items-center gap-3">
                                      <Badge className={taxType.color}>{taxType.type}</Badge>
                                      <span className="font-bold">{formatAmount(invoice.total_invoice_amount)}</span>
                                      {isExpanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                                    </div>
                                  </div>
                                  <p className="mt-2 text-sm text-muted-foreground">
                                    <span className="font-medium">To:</span> {invoice.service_receiver_name || 'Unknown'}
                                  </p>
                                </div>
                                
                                {isExpanded && (
                                  <div className="border-t bg-secondary/30 p-4">
                                    <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-4">
                                      <div className="bg-background p-3 rounded border">
                                        <p className="text-xs text-muted-foreground uppercase">Subtotal</p>
                                        <p className="font-semibold">{formatAmount(invoice.subtotal_fee_amount)}</p>
                                      </div>
                                      <div className="bg-background p-3 rounded border">
                                        <p className="text-xs text-muted-foreground uppercase">CGST</p>
                                        <p className="font-semibold text-emerald-600">{formatAmount(invoice.cgst_amount)}</p>
                                      </div>
                                      <div className="bg-background p-3 rounded border">
                                        <p className="text-xs text-muted-foreground uppercase">SGST</p>
                                        <p className="font-semibold text-emerald-600">{formatAmount(invoice.sgst_amount)}</p>
                                      </div>
                                      <div className="bg-background p-3 rounded border">
                                        <p className="text-xs text-muted-foreground uppercase">IGST</p>
                                        <p className="font-semibold text-blue-600">{formatAmount(invoice.igst_amount)}</p>
                                      </div>
                                      <div className="bg-background p-3 rounded border">
                                        <p className="text-xs text-muted-foreground uppercase">Total Tax</p>
                                        <p className="font-semibold text-orange-600">{formatAmount(invoice.total_tax_amount)}</p>
                                      </div>
                                    </div>
                                    
                                    {invoice.line_items && invoice.line_items.length > 0 && (
                                      <div className="overflow-x-auto">
                                        <Table>
                                          <TableHeader>
                                            <TableRow>
                                              <TableHead>HSN Code</TableHead>
                                              <TableHead>Description</TableHead>
                                              <TableHead className="text-right">Fee</TableHead>
                                              <TableHead className="text-right">Tax</TableHead>
                                              <TableHead className="text-right">Total</TableHead>
                                            </TableRow>
                                          </TableHeader>
                                          <TableBody>
                                            {invoice.line_items.map((item, itemIdx) => (
                                              <TableRow key={itemIdx}>
                                                <TableCell className="font-mono text-sm">{item.category_code_or_hsn || '-'}</TableCell>
                                                <TableCell>{item.service_description || '-'}</TableCell>
                                                <TableCell className="text-right">{formatAmount(item.fee_amount)}</TableCell>
                                                <TableCell className="text-right">{formatAmount(item.total_tax_amount)}</TableCell>
                                                <TableCell className="text-right font-semibold">{formatAmount(item.total_amount)}</TableCell>
                                              </TableRow>
                                            ))}
                                          </TableBody>
                                        </Table>
                                      </div>
                                    )}
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </CardContent>
                      </Card>
                    ))}
                  </TabsContent>

                  <TabsContent value="all-invoices">
                    <div className="overflow-x-auto">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Invoice #</TableHead>
                            <TableHead>Date</TableHead>
                            <TableHead>Provider</TableHead>
                            <TableHead>Receiver</TableHead>
                            <TableHead>Tax Type</TableHead>
                            <TableHead className="text-right">Total</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {extractedData.map((invoice, idx) => {
                            const taxType = getTaxType(invoice);
                            return (
                              <TableRow key={idx}>
                                <TableCell className="font-medium">{invoice.invoice_number || '-'}</TableCell>
                                <TableCell>{invoice.invoice_date || '-'}</TableCell>
                                <TableCell>
                                  <div>
                                    <p className="font-medium text-sm">{invoice.service_provider_name || '-'}</p>
                                    <p className="text-xs text-muted-foreground">{invoice.service_provider_gstin || '-'}</p>
                                  </div>
                                </TableCell>
                                <TableCell>
                                  <div>
                                    <p className="font-medium text-sm">{invoice.service_receiver_name || '-'}</p>
                                    <p className="text-xs text-muted-foreground">{invoice.service_receiver_gstin || '-'}</p>
                                  </div>
                                </TableCell>
                                <TableCell>
                                  <Badge className={taxType.color}>{taxType.type}</Badge>
                                </TableCell>
                                <TableCell className="text-right font-bold">{formatAmount(invoice.total_invoice_amount)}</TableCell>
                              </TableRow>
                            );
                          })}
                        </TableBody>
                      </Table>
                    </div>
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Right Column - Stats & Actions */}
        <div className="lg:col-span-4 space-y-6">
          {/* Stats Panel */}
          <Card className="bg-primary text-primary-foreground" data-testid="stats-panel">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm uppercase tracking-widest opacity-80">Extraction Status</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-4 mb-4">
                <div>
                  <p className="text-3xl font-bold">{totalFiles}</p>
                  <p className="text-xs opacity-70 uppercase">Total</p>
                </div>
                <div>
                  <p className="text-3xl font-bold text-emerald-300">{processedFiles - failedFiles}</p>
                  <p className="text-xs opacity-70 uppercase">Done</p>
                </div>
                <div>
                  <p className="text-3xl font-bold text-red-300">{failedFiles}</p>
                  <p className="text-xs opacity-70 uppercase">Failed</p>
                </div>
              </div>

              {isProcessing && (
                <div className="space-y-2">
                  <Progress value={progress} className="h-3" data-testid="progress-bar" />
                  <p className="text-xs opacity-70 text-right">{Math.round(progress)}% complete</p>
                </div>
              )}

              {isCompleted && (
                <div className="flex items-center gap-2 text-emerald-300">
                  <CheckCircle className="w-5 h-5" />
                  <span className="font-medium">Extraction Complete</span>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Action Buttons */}
          <div className="space-y-4">
            <Button
              data-testid="start-extraction-btn"
              onClick={handleStartExtraction}
              disabled={files.length === 0 || isProcessing || isCompleted}
              className="w-full py-6 text-lg font-bold"
            >
              {isProcessing ? (
                <>
                  <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Play className="w-5 h-5 mr-2" />
                  Start Extraction
                </>
              )}
            </Button>

            {isCompleted && extractedData.length > 0 && (
              <Button
                data-testid="view-data-btn"
                onClick={() => setShowDataView(!showDataView)}
                variant={showDataView ? "default" : "outline"}
                className="w-full"
              >
                <Eye className="w-5 h-5 mr-2" />
                {showDataView ? "Hide Data View" : "View Extracted Data"}
              </Button>
            )}

            {isCompleted && jobId && (
              <div className="flex gap-3">
                <a
                  href={`${API}/export/csv/${jobId}`}
                  download
                  data-testid="download-csv-btn"
                  className="flex-1"
                >
                  <Button variant="outline" className="w-full">
                    <Download className="w-4 h-4 mr-2" />
                    CSV
                  </Button>
                </a>
                <a
                  href={`${API}/export/excel/${jobId}`}
                  download
                  data-testid="download-excel-btn"
                  className="flex-1"
                >
                  <Button variant="outline" className="w-full">
                    <FileSpreadsheet className="w-4 h-4 mr-2" />
                    Excel
                  </Button>
                </a>
              </div>
            )}

            {(files.length > 0 || jobId) && (
              <Button
                data-testid="reset-btn"
                onClick={handleReset}
                variant="ghost"
                className="w-full text-destructive hover:text-destructive"
                disabled={isProcessing}
              >
                <Trash2 className="w-4 h-4 mr-2" />
                Reset / Clear All
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default InvoiceExtractor;
