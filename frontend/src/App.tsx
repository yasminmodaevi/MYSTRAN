import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';

const Layout = ({ children }: { children: React.ReactNode }) => (
  <div className="min-h-screen bg-gray-50 flex flex-col">
    <header className="bg-blue-900 text-white p-4 shadow-md flex justify-between items-center">
      <h1 className="text-xl font-bold tracking-tight">AeroPLM v0.1</h1>
      <nav className="flex gap-4">
        <Link to="/" className="hover:underline">Dashboard</Link>
        <Link to="/items" className="hover:underline">Items</Link>
        <Link to="/workflow" className="hover:underline">Workflows</Link>
      </nav>
    </header>
    <main className="flex-1 p-6">
      {children}
    </main>
    <footer className="p-4 text-center text-gray-500 text-sm border-t">
      AeroPLM | High-Performance Aerospace PLM
    </footer>
  </div>
);

const App = () => (
  <Router>
    <Layout>
      <Routes>
        <Route path="/" element={<div className="text-2xl font-semibold">Welcome to AeroPLM Dashboard</div>} />
        <Route path="/items" element={<div className="text-2xl font-semibold">Item Management</div>} />
        <Route path="/workflow" element={<div className="text-2xl font-semibold">Engineering Workflows</div>} />
      </Routes>
    </Layout>
  </Router>
);

export default App;
