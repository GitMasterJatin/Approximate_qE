import React from 'react';
import { Upload, Database, ArrowRight } from 'lucide-react';

interface DataSourceSelectorProps {
  onSelect: (source: 'upload' | 'existing') => void;
}

const DataSourceSelector: React.FC<DataSourceSelectorProps> = ({ onSelect }) => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900 to-violet-900 flex items-center justify-center p-4">
      <div className="max-w-4xl w-full">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-white mb-4">
            Data Analytics Platform
          </h1>
          <p className="text-lg text-gray-300 max-w-2xl mx-auto">
            Choose your data source to get started with intelligent SQL query analysis and optimization
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-8 max-w-3xl mx-auto">
          <div
            onClick={() => onSelect('upload')}
            className="bg-gray-800/50 backdrop-blur-sm rounded-2xl p-8 shadow-2xl hover:shadow-cyan-500/25 transition-all duration-300 cursor-pointer border border-gray-700 hover:border-cyan-400 group"
          >
            <div className="text-center">
              <div className="w-20 h-20 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-full flex items-center justify-center mx-auto mb-6 group-hover:from-cyan-400 group-hover:to-blue-500 transition-all duration-300 shadow-lg shadow-cyan-500/30">
                <Upload className="w-10 h-10 text-white" />
              </div>
              <h3 className="text-2xl font-semibold text-white mb-4">
                Upload Your CSV
              </h3>
              <p className="text-gray-300 mb-6 leading-relaxed">
                Upload your own CSV file to analyze custom datasets with our advanced query engine
              </p>
              <div className="flex items-center justify-center text-cyan-400 font-medium group-hover:text-cyan-300">
                Get Started
                <ArrowRight className="w-5 h-5 ml-2 group-hover:translate-x-1 transition-transform duration-300" />
              </div>
            </div>
          </div>

          <div
            onClick={() => onSelect('existing')}
            className="bg-gray-800/50 backdrop-blur-sm rounded-2xl p-8 shadow-2xl hover:shadow-emerald-500/25 transition-all duration-300 cursor-pointer border border-gray-700 hover:border-emerald-400 group"
          >
            <div className="text-center">
              <div className="w-20 h-20 bg-gradient-to-br from-emerald-500 to-green-600 rounded-full flex items-center justify-center mx-auto mb-6 group-hover:from-emerald-400 group-hover:to-green-500 transition-all duration-300 shadow-lg shadow-emerald-500/30">
                <Database className="w-10 h-10 text-white" />
              </div>
              <h3 className="text-2xl font-semibold text-white mb-4">
                Use Our Data
              </h3>
              <p className="text-gray-300 mb-6 leading-relaxed">
                Work with our curated sample datasets to explore the platform capabilities
              </p>
              <div className="flex items-center justify-center text-emerald-400 font-medium group-hover:text-emerald-300">
                Explore Now
                <ArrowRight className="w-5 h-5 ml-2 group-hover:translate-x-1 transition-transform duration-300" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DataSourceSelector;