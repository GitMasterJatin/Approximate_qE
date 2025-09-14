import React, { useState } from 'react';
import DataSourceSelector from './components/DataSourceSelector';
import FileUpload from './components/FileUpload';
import MainDashboard from './components/MainDashboard';

type AppState = 'select' | 'upload' | 'dashboard';
type DataSource = 'upload' | 'existing';

function App() {
  const [currentState, setCurrentState] = useState<AppState>('select');
  const [dataSource, setDataSource] = useState<DataSource>('existing');

  const handleDataSourceSelect = (source: DataSource) => {
    setDataSource(source);
    if (source === 'upload') {
      setCurrentState('upload');
    } else {
      setCurrentState('dashboard');
    }
  };

  const handleUploadNext = () => {
    setCurrentState('dashboard');
  };

  return (
    <div className="App">
      {currentState === 'select' && (
        <DataSourceSelector onSelect={handleDataSourceSelect} />
      )}
      
      {currentState === 'upload' && (
        <FileUpload onNext={handleUploadNext} />
      )}
      
      {currentState === 'dashboard' && (
        <MainDashboard dataSource={dataSource} />
      )}
    </div>
  );
}

export default App;