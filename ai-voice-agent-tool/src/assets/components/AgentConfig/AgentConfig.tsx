import React, { useState } from 'react';

const AgentConfig = () => {
  const [agentName, setAgentName] = useState<string>(''); 
  const [language, setLanguage] = useState<string>('English');
  const [voiceType, setVoiceType] = useState<string>('Male');

 
  const handleSubmit = (e: React.FormEvent<HTMLFormElement>): void => {
    e.preventDefault();
    console.log({ agentName, language, voiceType });
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow-lg hover:shadow-xl transition-shadow duration-300 mb-6">
      <h2 className="text-xl font-semibold mb-4 text-vite-green">Agent Configuration</h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block">Agent Name</label>
          <input
            type="text"
            value={agentName}
            onChange={(e) => setAgentName(e.target.value)}
            className="w-full p-2 border rounded focus:outline-none focus:ring-2 focus:ring-vite-green"
            required
          />
        </div>
        <div>
          <label className="block">Language</label>
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            className="w-full p-2 border rounded focus:outline-none focus:ring-2 focus:ring-vite-green"
          >
            <option value="English">English</option>
            <option value="Spanish">Spanish</option>
            <option value="Arabic">Arabic</option>
          </select>
        </div>
        <div>
          <label className="block">Voice Type</label>
          <select
            value={voiceType}
            onChange={(e) => setVoiceType(e.target.value)}
            className="w-full p-2 border rounded focus:outline-none focus:ring-2 focus:ring-vite-green"
          >
            <option value="Male">Male</option>
            <option value="Female">Female</option>
          </select>
        </div>
        <button
          type="submit"
          className="w-full p-2 bg-vite-green text-white rounded hover:bg-green-600 transition-colors"
        >
          Save Configuration
        </button>
      </form>
    </div>
  );
};

export default AgentConfig;
