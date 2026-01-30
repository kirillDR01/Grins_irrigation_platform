import React, { useState } from 'react';
import { 
  LayoutDashboard, 
  Users, 
  Briefcase, 
  Calendar, 
  MapPin, 
  FileText, 
  Settings, 
  Search, 
  Bell, 
  Plus, 
  MoreHorizontal, 
  Sparkles, 
  X,
  CheckCircle2,
  Clock,
  AlertCircle,
  ChevronRight,
  Filter,
  Download
} from 'lucide-react';

// --- Types ---

interface Customer {
  id: string;
  name: string;
  phone: string;
  email: string;
  source: string;
  status: 'New' | 'Active' | 'Inactive';
  tags: string[];
}

interface Job {
  id: string;
  type: string;
  status: 'Scheduled' | 'Completed' | 'Pending' | 'Approved';
  category: 'Ready' | 'Needs Estimate' | 'Urgent';
  priority: 'Normal' | 'High' | 'Urgent';
  date: string;
  amount?: number;
}

// --- Mock Data ---

const MOCK_CUSTOMERS: Customer[] = [
  { id: '1', name: 'Jane Anderson', phone: '612-260-6377', email: 'jane.anderson@outlook.com', source: 'Referral', status: 'New', tags: ['New Customer'] },
  { id: '2', name: 'Christopher Anderson', phone: '612-738-5301', email: 'christopher.anderson@yahoo.com', source: 'Referral', status: 'Active', tags: [] },
  { id: '3', name: 'John Anderson', phone: '612-186-7368', email: 'john.anderson@icloud.com', source: 'Word of Mouth', status: 'Active', tags: ['Priority'] },
  { id: '4', name: 'Rebecca Brown', phone: '612-971-7040', email: 'rebecca.brown@gmail.com', source: 'Google', status: 'Active', tags: [] },
  { id: '5', name: 'Brian Brown', phone: '612-787-5393', email: 'brian.brown@yahoo.com', source: 'Website', status: 'Active', tags: [] },
];

const MOCK_JOBS: Job[] = [
  { id: '101', type: 'Repair', status: 'Completed', category: 'Ready', priority: 'Normal', date: '1/29/2026', amount: 75.00 },
  { id: '102', type: 'Repair', status: 'Scheduled', category: 'Ready', priority: 'Normal', date: '1/24/2026' },
  { id: '103', type: 'Spring Startup', status: 'Scheduled', category: 'Ready', priority: 'Normal', date: '1/24/2026' },
  { id: '104', type: 'Tune Up', status: 'Scheduled', category: 'Ready', priority: 'High', date: '1/24/2026' },
  { id: '105', type: 'Installation', status: 'Approved', category: 'Needs Estimate', priority: 'Normal', date: '1/24/2026' },
];

// --- Components ---

const SidebarItem = ({ 
  icon: Icon, 
  label, 
  active, 
  onClick 
}: { 
  icon: React.ElementType, 
  label: string, 
  active: boolean, 
  onClick: () => void 
}) => (
  <button
    onClick={onClick}
    className={`w-full flex items-center gap-4 px-6 py-4 transition-all duration-200 relative group
      ${active ? 'text-teal-600 font-medium bg-teal-50/50' : 'text-slate-400 hover:text-slate-600 hover:bg-slate-50'}
    `}
  >
    {active && (
      <div className="absolute left-0 top-0 bottom-0 w-1 bg-teal-500 rounded-r-full" />
    )}
    <Icon size={20} strokeWidth={active ? 2.5 : 2} />
    <span className="text-sm tracking-wide">{label}</span>
  </button>
);

const StatCard = ({ title, value, subtext, icon: Icon, colorClass }: any) => (
  <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 hover:shadow-md transition-shadow">
    <div className="flex justify-between items-start mb-4">
      <div>
        <h3 className="text-slate-400 text-sm font-medium uppercase tracking-wider">{title}</h3>
        <p className="text-3xl font-bold text-slate-800 mt-2">{value}</p>
      </div>
      <div className={`p-3 rounded-xl ${colorClass}`}>
        <Icon size={20} className="text-white" />
      </div>
    </div>
    {subtext && <p className="text-slate-400 text-xs">{subtext}</p>}
  </div>
);

interface StatusBadgeProps {
  status: string;
  type?: 'job' | 'default';
}

const StatusBadge: React.FC<StatusBadgeProps> = ({ status, type = 'default' }) => {
  let styles = "bg-slate-100 text-slate-600";
  
  if (type === 'job') {
    switch (status) {
      case 'Completed': styles = "bg-emerald-100 text-emerald-700"; break;
      case 'Scheduled': styles = "bg-violet-100 text-violet-700"; break;
      case 'Approved': styles = "bg-blue-100 text-blue-700"; break;
      case 'Ready': styles = "bg-emerald-50 text-emerald-600 border border-emerald-100"; break;
      case 'Needs Estimate': styles = "bg-amber-50 text-amber-600 border border-amber-100"; break;
      default: styles = "bg-slate-100 text-slate-600";
    }
  } else {
    // Customer tags/status
    if (status === 'New Customer') styles = "bg-blue-50 text-blue-600 border border-blue-100";
    if (status === 'Priority') styles = "bg-rose-50 text-rose-600 border border-rose-100";
    if (status === 'New') styles = "bg-teal-50 text-teal-600";
  }

  return (
    <span className={`px-3 py-1 rounded-full text-xs font-medium ${styles}`}>
      {status}
    </span>
  );
};

const ButtonPrimary = ({ children, icon: Icon, onClick, className = "" }: any) => (
  <button 
    onClick={onClick}
    className={`bg-teal-500 hover:bg-teal-600 text-white px-5 py-2.5 rounded-lg text-sm font-medium flex items-center gap-2 shadow-sm shadow-teal-200 transition-all ${className}`}
  >
    {Icon && <Icon size={16} />}
    {children}
  </button>
);

const ButtonSecondary = ({ children, icon: Icon, onClick, className = "" }: any) => (
  <button 
    onClick={onClick}
    className={`bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 px-4 py-2.5 rounded-lg text-sm font-medium flex items-center gap-2 transition-all ${className}`}
  >
    {Icon && <Icon size={16} />}
    {children}
  </button>
);

// --- Modals ---

const AICategorizeModal = ({ isOpen, onClose }: { isOpen: boolean, onClose: () => void }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-slate-900/20 backdrop-blur-sm" onClick={onClose} />
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg relative z-10 overflow-hidden animate-in fade-in zoom-in duration-200">
        <div className="p-6 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
          <div className="flex items-center gap-2">
            <Sparkles className="text-teal-500" size={20} />
            <h3 className="font-semibold text-slate-800">AI Job Categorization</h3>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <X size={20} />
          </button>
        </div>
        
        <div className="p-6 space-y-4">
          <p className="text-sm text-slate-500">
            Enter a job description below and let our AI analyze urgency, categorize the request, and suggest services.
          </p>
          
          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase text-slate-400 tracking-wider">Job Description</label>
            <textarea 
              className="w-full h-32 p-4 rounded-xl border border-slate-200 focus:border-teal-500 focus:ring-2 focus:ring-teal-100 outline-none resize-none text-slate-700 text-sm"
              placeholder="e.g., My sprinkler heads are broken and water is spraying everywhere. Need someone to fix it ASAP."
              defaultValue="My sprinkler heads are broken and water is spraying everywhere. Need someone to fix it ASAP."
            />
          </div>

          <div className="bg-teal-50 p-4 rounded-xl border border-teal-100 flex gap-4 items-start">
            <div className="bg-teal-100 p-2 rounded-lg shrink-0">
              <CheckCircle2 size={18} className="text-teal-600" />
            </div>
            <div>
              <h4 className="text-sm font-semibold text-teal-800">AI Prediction Preview</h4>
              <div className="mt-2 flex flex-wrap gap-2">
                <span className="bg-white text-teal-700 px-2 py-1 rounded text-xs font-medium border border-teal-100">Category: Urgent</span>
                <span className="bg-white text-teal-700 px-2 py-1 rounded text-xs font-medium border border-teal-100">Confidence: 95%</span>
              </div>
            </div>
          </div>
        </div>

        <div className="p-6 border-t border-slate-100 flex justify-end gap-3 bg-slate-50/50">
          <ButtonSecondary onClick={onClose}>Cancel</ButtonSecondary>
          <ButtonPrimary icon={Sparkles}>Categorize Job</ButtonPrimary>
        </div>
      </div>
    </div>
  );
};

// --- Views ---

const DashboardView = () => (
  <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Dashboard</h1>
        <p className="text-slate-500 mt-1">Hello, Viktor! Here's what's happening today.</p>
      </div>
      <div className="flex gap-3">
        <ButtonSecondary icon={Calendar}>View Schedule</ButtonSecondary>
        <ButtonPrimary icon={Plus}>New Job</ButtonPrimary>
      </div>
    </div>

    {/* Alerts Section (Inspired by Fittle notifications) */}
    <div className="space-y-4">
      <div className="bg-white p-4 rounded-xl shadow-sm border-l-4 border-amber-400 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="bg-amber-100 p-2 rounded-full">
            <AlertCircle className="text-amber-600" size={20} />
          </div>
          <div>
            <p className="text-slate-800 font-medium">Overnight Requests</p>
            <p className="text-slate-500 text-sm">You have 3 new job requests from last night.</p>
          </div>
        </div>
        <button className="text-sm font-medium text-amber-600 hover:text-amber-700 bg-amber-50 px-4 py-2 rounded-lg">Review</button>
      </div>
    </div>

    {/* Stats Grid */}
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <StatCard 
        title="Today's Schedule" 
        value="8" 
        subtext="2 Jobs in progress" 
        icon={Calendar} 
        colorClass="bg-teal-500" 
      />
      <StatCard 
        title="Pending Messages" 
        value="12" 
        subtext="Requires attention" 
        icon={FileText} 
        colorClass="bg-violet-500" 
      />
      <StatCard 
        title="Outstanding Invoices" 
        value="$3,450" 
        subtext="5 Invoices overdue" 
        icon={Briefcase} 
        colorClass="bg-emerald-500" 
      />
       <StatCard 
        title="Active Staff" 
        value="4" 
        subtext="1 on Leave" 
        icon={Users} 
        colorClass="bg-blue-500" 
      />
    </div>

    {/* Recent Activity Section */}
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
      <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
        <div className="flex justify-between items-center mb-6">
          <h3 className="font-bold text-slate-800 text-lg">Recent Jobs</h3>
          <button className="text-teal-600 text-sm font-medium hover:text-teal-700 flex items-center gap-1">
            View All <ChevronRight size={14} />
          </button>
        </div>
        <div className="space-y-4">
          {MOCK_JOBS.slice(0, 3).map((job) => (
            <div key={job.id} className="flex items-center justify-between p-4 bg-slate-50 rounded-xl hover:bg-slate-100 transition-colors cursor-pointer group">
              <div className="flex items-center gap-4">
                <div className="bg-white p-3 rounded-lg shadow-sm group-hover:shadow text-teal-600">
                  <Briefcase size={18} />
                </div>
                <div>
                  <h4 className="font-semibold text-slate-800">{job.type}</h4>
                  <p className="text-xs text-slate-500">{job.date} • ID #{job.id}</p>
                </div>
              </div>
              <StatusBadge status={job.status} type="job" />
            </div>
          ))}
        </div>
      </div>

      <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
         <div className="flex justify-between items-center mb-6">
          <h3 className="font-bold text-slate-800 text-lg">Technician Availability</h3>
          <button className="text-teal-600 text-sm font-medium hover:text-teal-700 flex items-center gap-1">
            Manage <ChevronRight size={14} />
          </button>
        </div>
        <div className="space-y-6">
            {[
              { name: 'Viktor Grin', status: 'Available', time: 'Until 4:00 PM' },
              { name: 'Steven Miller', status: 'On Job', time: 'Back at 2:30 PM' },
              { name: 'Vas Tech', status: 'Available', time: 'Until 5:00 PM' },
            ].map((tech, i) => (
              <div key={i} className="flex items-center justify-between border-b border-slate-50 pb-4 last:border-0 last:pb-0">
                <div className="flex items-center gap-3">
                   <div className="w-10 h-10 rounded-full bg-slate-200 flex items-center justify-center text-slate-600 font-semibold text-sm">
                      {tech.name.charAt(0)}
                   </div>
                   <div>
                     <p className="text-sm font-medium text-slate-800">{tech.name}</p>
                     <p className="text-xs text-slate-500">{tech.time}</p>
                   </div>
                </div>
                <div className="flex items-center gap-2">
                   <div className={`w-2 h-2 rounded-full ${tech.status === 'Available' ? 'bg-emerald-500' : 'bg-amber-500'}`} />
                   <span className="text-xs font-medium text-slate-600">{tech.status}</span>
                </div>
              </div>
            ))}
        </div>
      </div>
    </div>
  </div>
);

const CustomersView = () => (
  <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Customers</h1>
        <p className="text-slate-500 mt-1">Manage your customer database and properties.</p>
      </div>
      <ButtonPrimary icon={Plus}>Add Customer</ButtonPrimary>
    </div>

    <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
      {/* Table Toolbar */}
      <div className="p-4 border-b border-slate-100 flex gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
          <input 
            type="text" 
            placeholder="Search customers..." 
            className="w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500 transition-all"
          />
        </div>
        <ButtonSecondary icon={Filter}>Filter</ButtonSecondary>
        <ButtonSecondary icon={Download}>Export</ButtonSecondary>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-slate-50/50 text-slate-500 text-xs uppercase tracking-wider">
              <th className="px-6 py-4 font-medium">Name</th>
              <th className="px-6 py-4 font-medium">Contact</th>
              <th className="px-6 py-4 font-medium">Source</th>
              <th className="px-6 py-4 font-medium">Flags</th>
              <th className="px-6 py-4 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {MOCK_CUSTOMERS.map((customer) => (
              <tr key={customer.id} className="hover:bg-slate-50/80 transition-colors group">
                <td className="px-6 py-4">
                  <span className="font-semibold text-slate-700 block">{customer.name}</span>
                </td>
                <td className="px-6 py-4">
                  <div className="flex flex-col gap-1">
                     <span className="text-sm text-slate-600 flex items-center gap-2">
                        {customer.phone}
                     </span>
                     <span className="text-xs text-slate-400">{customer.email}</span>
                  </div>
                </td>
                <td className="px-6 py-4 text-sm text-slate-600">{customer.source}</td>
                <td className="px-6 py-4">
                   <div className="flex gap-2">
                      {customer.tags.map(tag => (
                        <StatusBadge key={tag} status={tag} />
                      ))}
                      {customer.tags.length === 0 && <span className="text-slate-300 text-sm">-</span>}
                   </div>
                </td>
                <td className="px-6 py-4 text-right">
                  <button className="text-slate-400 hover:text-teal-600 p-2 hover:bg-teal-50 rounded-lg transition-colors">
                    <MoreHorizontal size={18} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {/* Pagination Mock */}
      <div className="p-4 border-t border-slate-100 flex justify-between items-center text-sm text-slate-500">
        <span>Showing 1-5 of 124 customers</span>
        <div className="flex gap-2">
          <button className="px-3 py-1 border border-slate-200 rounded hover:bg-slate-50 disabled:opacity-50">Prev</button>
          <button className="px-3 py-1 border border-slate-200 rounded hover:bg-slate-50">Next</button>
        </div>
      </div>
    </div>
  </div>
);

const JobsView = () => {
  const [isAIModalOpen, setIsAIModalOpen] = useState(false);

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Jobs</h1>
          <p className="text-slate-500 mt-1">Manage job requests and track status.</p>
        </div>
        <div className="flex gap-3">
          <ButtonSecondary icon={Sparkles} onClick={() => setIsAIModalOpen(true)}>AI Categorize</ButtonSecondary>
          <ButtonPrimary icon={Plus}>New Job</ButtonPrimary>
        </div>
      </div>

      <AICategorizeModal isOpen={isAIModalOpen} onClose={() => setIsAIModalOpen(false)} />

      <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
        <div className="p-4 border-b border-slate-100 flex gap-4">
          <div className="relative flex-1 max-w-md">
             <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
             <input type="text" placeholder="Search jobs..." className="w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500 transition-all" />
          </div>
          <select className="px-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-600 focus:outline-none">
             <option>All Statuses</option>
             <option>Scheduled</option>
             <option>Pending</option>
          </select>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50/50 text-slate-500 text-xs uppercase tracking-wider">
                <th className="px-6 py-4 font-medium">Job Type</th>
                <th className="px-6 py-4 font-medium">Status</th>
                <th className="px-6 py-4 font-medium">Category</th>
                <th className="px-6 py-4 font-medium">Priority</th>
                <th className="px-6 py-4 font-medium">Amount</th>
                <th className="px-6 py-4 font-medium">Created</th>
                <th className="px-6 py-4 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {MOCK_JOBS.map((job) => (
                <tr key={job.id} className="hover:bg-slate-50/80 transition-colors">
                  <td className="px-6 py-4 font-medium text-slate-700">{job.type}</td>
                  <td className="px-6 py-4"><StatusBadge status={job.status} type="job" /></td>
                  <td className="px-6 py-4"><StatusBadge status={job.category} type="job" /></td>
                  <td className="px-6 py-4">
                    <span className={`text-xs font-semibold px-2 py-1 rounded ${
                      job.priority === 'High' ? 'bg-orange-50 text-orange-600' : 'text-slate-500 bg-slate-100'
                    }`}>
                      {job.priority}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-slate-600">
                    {job.amount ? `$${job.amount.toFixed(2)}` : <span className="text-slate-400 italic">Not quoted</span>}
                  </td>
                  <td className="px-6 py-4 text-sm text-slate-500">{job.date}</td>
                  <td className="px-6 py-4 text-right">
                    <button className="text-slate-400 hover:text-teal-600 p-2 hover:bg-teal-50 rounded-lg transition-colors">
                      <MoreHorizontal size={18} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

// --- Main App & Layout ---

export default function App() {
  const [activeTab, setActiveTab] = useState('Dashboard');

  const renderContent = () => {
    switch (activeTab) {
      case 'Dashboard': return <DashboardView />;
      case 'Customers': return <CustomersView />;
      case 'Jobs': return <JobsView />;
      default: return (
        <div className="flex flex-col items-center justify-center h-[50vh] text-slate-400 animate-in fade-in">
          <Settings size={48} className="mb-4 opacity-50" />
          <h2 className="text-lg font-medium">Work in Progress</h2>
          <p>The {activeTab} view is currently being redesigned.</p>
        </div>
      );
    }
  };

  return (
    <div className="flex h-screen bg-[#F8FAFC] text-slate-800 font-sans overflow-hidden selection:bg-teal-100 selection:text-teal-800">
      
      {/* Sidebar */}
      <aside className="w-64 bg-white hidden md:flex flex-col border-r border-slate-100 shadow-sm z-20">
        <div className="p-6 flex items-center gap-3">
          <div className="w-8 h-8 bg-teal-500 rounded-lg flex items-center justify-center shadow-lg shadow-teal-500/30">
             <div className="w-4 h-4 border-2 border-white rounded-full border-t-transparent animate-spin-slow" />
          </div>
          <span className="text-lg font-bold tracking-tight text-slate-900">Grin's<span className="text-teal-500">.</span></span>
        </div>

        <nav className="flex-1 py-4 space-y-1 overflow-y-auto">
          <SidebarItem icon={LayoutDashboard} label="Dashboard" active={activeTab === 'Dashboard'} onClick={() => setActiveTab('Dashboard')} />
          <SidebarItem icon={Users} label="Customers" active={activeTab === 'Customers'} onClick={() => setActiveTab('Customers')} />
          <SidebarItem icon={Briefcase} label="Jobs" active={activeTab === 'Jobs'} onClick={() => setActiveTab('Jobs')} />
          <SidebarItem icon={Calendar} label="Schedule" active={activeTab === 'Schedule'} onClick={() => setActiveTab('Schedule')} />
          <SidebarItem icon={MapPin} label="Generate Routes" active={activeTab === 'Routes'} onClick={() => setActiveTab('Routes')} />
          <SidebarItem icon={Users} label="Staff" active={activeTab === 'Staff'} onClick={() => setActiveTab('Staff')} />
          <SidebarItem icon={FileText} label="Invoices" active={activeTab === 'Invoices'} onClick={() => setActiveTab('Invoices')} />
        </nav>

        <div className="p-4 border-t border-slate-100">
           <SidebarItem icon={Settings} label="Settings" active={activeTab === 'Settings'} onClick={() => setActiveTab('Settings')} />
           
           <div className="mt-4 p-4 bg-slate-50 rounded-xl flex items-center gap-3 cursor-pointer hover:bg-slate-100 transition-colors">
              <img src="https://picsum.photos/100/100" alt="Admin" className="w-10 h-10 rounded-full object-cover border-2 border-white shadow-sm" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-slate-800 truncate">Admin User</p>
                <p className="text-xs text-slate-500 truncate">admin@grins.com</p>
              </div>
           </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col h-screen overflow-hidden relative">
        {/* Top Header */}
        <header className="h-16 bg-white/80 backdrop-blur-md border-b border-slate-100 flex items-center justify-between px-8 z-10 sticky top-0">
          <div className="flex items-center gap-4 text-slate-400">
             <Search size={20} />
             <input 
               type="text" 
               placeholder="Search..." 
               className="bg-transparent border-none outline-none text-sm w-64 text-slate-600 placeholder-slate-400"
             />
          </div>
          <div className="flex items-center gap-6">
            <button className="relative text-slate-400 hover:text-teal-600 transition-colors">
              <Bell size={20} />
              <span className="absolute top-0 right-0 w-2 h-2 bg-rose-500 rounded-full border-2 border-white"></span>
            </button>
            <div className="h-8 w-px bg-slate-200"></div>
            <div className="flex items-center gap-2">
               <div className="w-8 h-8 rounded-full bg-teal-100 text-teal-700 flex items-center justify-center font-bold text-xs">
                  AU
               </div>
            </div>
          </div>
        </header>

        {/* Page Content Scroll Area */}
        <div className="flex-1 overflow-y-auto p-8 scroll-smooth">
          <div className="max-w-7xl mx-auto">
            {renderContent()}
          </div>
        </div>
      </main>
    </div>
  );
}