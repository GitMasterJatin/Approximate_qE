'use client';

import React, { useState, useRef } from 'react';
import { Upload, File, CheckCircle, ArrowRight, ArrowLeft } from 'lucide-react';
import { useRouter } from 'next/navigation';

const FileUpload: React.FC = () => {
  const router = useRouter();
  const [dragActive, setDragActive] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [dimCols, setDimCols] = useState<string>('');
  const [numericCols, setNumericCols] = useState<string>('');
  const [distinctCols, setDistinctCols] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false); // New state for loading
  const [loadingMessage, setLoadingMessage] = useState(''); // New state for loading message
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    const files = e.dataTransfer.files;
    if (files && files[0] && files[0].type === 'text/csv') {
      setUploadedFile(files[0]);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files[0]) {
      setUploadedFile(files[0]);
    }
  };

  const openFileDialog = () => {
    fileInputRef.current?.click();
  };

  const handleNext = async () => {
    if (!uploadedFile) {
      setError('Please upload a CSV file first.');
      return;
    }

    setError(null); // Clear previous errors

    setLoading(true); // Start loading
    setLoadingMessage("Sending request...");

    const formData = new FormData();
    formData.append('file', uploadedFile);
    formData.append('dim_cols', dimCols);
    formData.append('numeric_cols', numericCols);
    formData.append('distinct_cols', distinctCols);

    try {
      const response = await fetch('http://127.0.0.1:5000/upload', {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        setLoadingMessage("Building sketches..."); // Update message
        const queryParams = new URLSearchParams();
        queryParams.append('fileName', uploadedFile.name);
        if (dimCols) {
          queryParams.append('dimCols', dimCols);
        }
        if (numericCols) {
          queryParams.append('numericCols', numericCols);
        }
        if (distinctCols) {
          queryParams.append('distinctCols', distinctCols);
        }
        setLoadingMessage("Completing..."); // Update message before navigation
        router.push(`/dashboard?${queryParams.toString()}`);
      } else {
        const errorData = await response.json();
        setError(errorData.message || 'File upload failed.');
      }
    } catch (err) {
      setError('Network error or server is unreachable.');
    } finally {
      setLoading(false); // End loading
      setLoadingMessage(''); // Clear loading message
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-indigo-900 to-purple-900 flex items-center justify-center p-4">
      <div className="max-w-2xl w-full">
        {/* Back Button */}
        <div className="mb-6">
          <button
            onClick={() => router.push('/data-source')}
            className="flex items-center text-gray-300 hover:text-white transition-colors duration-300"
          >
            <ArrowLeft className="w-5 h-5 mr-2" />
            Back to Data Source Selection
          </button>
        </div>

        <div className="text-center mb-8">
          <h2 className="text-3xl font-bold text-white mb-4">
            Upload Your CSV File
          </h2>
          <p className="text-lg text-gray-300">
            Drag and drop your CSV file or click to browse
          </p>
        </div>

        <div className="bg-gray-800/50 backdrop-blur-sm rounded-2xl p-8 shadow-2xl border border-gray-700">
          <div
            className={`border-2 border-dashed rounded-xl p-12 text-center transition-all duration-300 ${
              dragActive
                ? 'border-cyan-400 bg-cyan-500/10'
                : uploadedFile
                ? 'border-emerald-400 bg-emerald-500/10'
                : 'border-gray-600 hover:border-cyan-400 hover:bg-cyan-500/5'
            }`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            onClick={openFileDialog}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv"
              onChange={handleFileSelect}
              className="hidden"
            />
            
            {uploadedFile ? (
              <div className="space-y-4">
                <CheckCircle className="w-16 h-16 text-emerald-400 mx-auto" />
                <div>
                  <h3 className="text-xl font-semibold text-white">File Uploaded Successfully!</h3>
                  <p className="text-gray-300 mt-2">{uploadedFile.name}</p>
                  <p className="text-sm text-gray-400">
                    Size: {(uploadedFile.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <Upload className="w-16 h-16 text-gray-500 mx-auto" />
                <div>
                  <h3 className="text-xl font-semibold text-gray-200">
                    Drop your CSV file here
                  </h3>
                  <p className="text-gray-400 mt-2">
                    or click to browse your files
                  </p>
                </div>
                <p className="text-sm text-gray-500">
                  Supported format: CSV (max 100MB)
                </p>
              </div>
            )}
          </div>

          {error && (
            <div className="mt-4 text-red-400 text-center">
              {error}
            </div>
          )}

          {uploadedFile && (
            <div className="mt-6 space-y-4">
              <div>
                <label htmlFor="dim_cols" className="block text-gray-300 text-sm font-medium mb-2">
                  Dimension Columns (comma-separated)
                </label>
                <input
                  type="text"
                  id="dim_cols"
                  value={dimCols}
                  onChange={(e) => setDimCols(e.target.value)}
                  className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:ring-cyan-500 focus:border-cyan-500"
                  placeholder="e.g., city, country, product_category"
                />
              </div>
              <div>
                <label htmlFor="numeric_cols" className="block text-gray-300 text-sm font-medium mb-2">
                  Numeric Columns (comma-separated)
                </label>
                <input
                  type="text"
                  id="numeric_cols"
                  value={numericCols}
                  onChange={(e) => setNumericCols(e.target.value)}
                  className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:ring-cyan-500 focus:border-cyan-500"
                  placeholder="e.g., price, quantity, sales"
                />
              </div>
              <div>
                <label htmlFor="distinct_cols" className="block text-gray-300 text-sm font-medium mb-2">
                  Distinct Count Columns (comma-separated)
                </label>
                <input
                  type="text"
                  id="distinct_cols"
                  value={distinctCols}
                  onChange={(e) => setDistinctCols(e.target.value)}
                  className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:ring-cyan-500 focus:border-cyan-500"
                  placeholder="e.g., customer_id, order_id"
                />
              </div>
            </div>
          )}

          {uploadedFile && (
            <div className="mt-8 flex justify-center">
              <button
                onClick={handleNext}
                className="bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white px-8 py-3 rounded-lg font-medium flex items-center transition-all duration-300 shadow-lg shadow-cyan-500/30"
                disabled={loading}
              >
                {loading ? (
                  <div className="flex items-center">
                    <svg className="animate-spin h-5 w-5 text-white mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    {loadingMessage}
                  </div>
                ) : (
                  <>
                    Continue to Dashboard
                    <ArrowRight className="w-5 h-5 ml-2" />
                  </>
                )}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default FileUpload;
