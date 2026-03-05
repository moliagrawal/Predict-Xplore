import React, { useState } from 'react';
import axios from 'axios';
import { toast } from 'react-toastify';
import { FaGithub, FaSync } from 'react-icons/fa';

const GithubContainerWizard = ({ githubUrl, setGithubUrl, selectedFolder, setSelectedFolder, token }) => {
    const [folders, setFolders] = useState([]);
    const [isFetching, setIsFetching] = useState(false);

    const fetchFolders = async () => {
        if (!githubUrl) {
            toast.error('Please enter a GitHub URL first');
            return;
        }

        try {
            setIsFetching(true);
            const response = await axios.get(`http://127.0.0.1:8000/model/github/tree/?repo_url=${encodeURIComponent(githubUrl)}`, {
                headers: { Authorization: `Token ${token}` }
            });
            setFolders(response.data.folders);
            setSelectedFolder('/'); // Default to root
            toast.success('Folders fetched successfully!');
        } catch (error) {
            console.error(error);
            toast.error(error.response?.data?.error || 'Failed to fetch folders. Is the repo public and url correct?');
            setFolders([]);
        } finally {
            setIsFetching(false);
        }
    };

    return (
        <div className="w-full bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
            <div className="flex items-center gap-2 mb-4 text-xl font-bold text-gray-800">
                <FaGithub className="text-2xl" />
                <h3>Link GitHub Repository</h3>
            </div>

            <div className="flex flex-col space-y-4">
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Repository URL</label>
                    <div className="flex">
                        <input
                            type="text"
                            className="flex-1 rounded-l-md border border-gray-300 px-4 py-2 focus:ring-blue-500 focus:border-blue-500"
                            placeholder="https://github.com/username/repository"
                            value={githubUrl}
                            onChange={(e) => setGithubUrl(e.target.value)}
                        />
                        <button
                            type="button"
                            onClick={fetchFolders}
                            disabled={isFetching || !githubUrl}
                            className="bg-gray-800 hover:bg-gray-900 text-white px-4 py-2 rounded-r-md font-medium transition-colors flex items-center gap-2"
                            style={{ opacity: (isFetching || !githubUrl) ? 0.5 : 1 }}
                        >
                            {isFetching ? <FaSync className="animate-spin" /> : 'Fetch Folders'}
                        </button>
                    </div>
                </div>

                {folders.length > 0 && (
                    <div className="animate-fade-in">
                        <label className="block text-sm font-medium text-gray-700 mb-1">Select Container Root Folder</label>
                        <select
                            className="w-full rounded-md border border-gray-300 px-4 py-2 focus:ring-blue-500 focus:border-blue-500 bg-gray-50 mb-2"
                            value={selectedFolder}
                            onChange={(e) => setSelectedFolder(e.target.value)}
                        >
                            <option value="" disabled>-- Select a folder --</option>
                            {folders.map(folder => (
                                <option key={folder} value={folder}>{folder === '/' ? 'Root Directory (/)' : folder}</option>
                            ))}
                        </select>
                        <p className="mt-2 text-sm text-gray-500">
                            The selected folder must contain your <code className="bg-gray-200 px-1 rounded">Dockerfile</code>,
                            <code className="bg-gray-200 px-1 rounded ml-1">requirements.txt</code>, and
                            <code className="bg-gray-200 px-1 rounded ml-1">inference.py</code>.
                        </p>
                    </div>
                )}
            </div>
        </div>
    );
};

export default GithubContainerWizard;
