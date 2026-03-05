import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'react-toastify';
import AdminNavbar from '../../components/AdminNavbar';
import { FaTrash, FaInfoCircle, FaGithub, FaSync } from 'react-icons/fa';
import { useNavigate } from 'react-router-dom';
import { useSelector } from 'react-redux';

const Containers = () => {
    const [containers, setContainers] = useState([]);
    const [selectedContainer, setSelectedContainer] = useState(null);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [updateInfo, setUpdateInfo] = useState(null);
    const [isCheckingUpdate, setIsCheckingUpdate] = useState(false);
    const navigate = useNavigate();

    const user = useSelector(
        (state) => state.user.users[state.user.users.length - 1]
    );
    const token = user?.token;

    useEffect(() => {
        fetchContainers();
    }, []);

    const fetchContainers = async () => {
        try {
            const response = await axios.get('http://127.0.0.1:8000/model/list-container/', {
                headers: { Authorization: `Token ${token} ` },
            });
            if (response.data && response.data.containers) {
                setContainers(response.data.containers);
            }
        } catch (error) {
            console.error('Error fetching containers:', error);
            toast.error('Failed to load containers');
        }
    };

    const handleDelete = async (containerId) => {
        if (!window.confirm("Are you sure you want to delete this container? This action cannot be undone.")) return;

        try {
            await axios.delete('http://127.0.0.1:8000/model/container-management/', {
                data: { container_id: containerId },
                headers: { Authorization: `Token ${token} ` },
            });
            toast.success("Container deleted successfully");
            fetchContainers();
        } catch (error) {
            toast.error("Failed to delete container");
            console.error(error);
        }
    };

    const openDetails = (container) => {
        setSelectedContainer(container);
        setUpdateInfo(null);
        setIsModalOpen(true);
    };

    const checkUpdate = async () => {
        if (!selectedContainer) return;
        setIsCheckingUpdate(true);
        try {
            const res = await axios.get(`http://127.0.0.1:8000/model/container-management/?container_id=${selectedContainer.id}`, {
                headers: { Authorization: `Token ${token}` },
            });
            setUpdateInfo(res.data);
            if (res.data.update_available) {
                toast.info("An update is available from GitHub!");
            } else {
                toast.success("Container is up-to-date with GitHub.");
            }
        } catch (error) {
            toast.error("Failed to check for updates");
            console.error(error);
        } finally {
            setIsCheckingUpdate(false);
        }
    };

    const pullUpdate = async () => {
        if (!selectedContainer || !updateInfo) return;
        try {
            const res = await axios.post('http://127.0.0.1:8000/model/container-update/', {
                container_id: selectedContainer.id,
                target_hash: updateInfo.remote_hash
            }, {
                headers: { Authorization: `Token ${token}` },
            });
            toast.success(`Update task started! Task ID: ${res.data.task_id}`);
            setIsModalOpen(false);
            navigate('/admin/tasks');
        } catch (error) {
            toast.error("Failed to start update task");
            console.error(error);
        }
    };

    return (
        <div className="h-screen w-screen bg-[#EAECFF] overflow-auto">
            <AdminNavbar />
            <div className="flex flex-col mx-20 mt-6">
                <main className="flex-1 p-6 overflow-y-auto">
                    <div className="flex justify-between items-center mb-6">
                        <h1 className="text-3xl font-bold text-gray-800">Container Management</h1>
                        <button
                            onClick={() => navigate('/admin/create-model')}
                            className="bg-[#6966FF] hover:bg-blue-800 text-white font-bold py-2 px-6 rounded-full transition duration-200 shadow-md"
                        >
                            Add New Container
                        </button>
                    </div>

                    <div className="bg-white rounded-2xl shadow-md overflow-hidden p-4">
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50 border-b">
                                <tr>
                                    <th className="px-6 py-4 text-left text-sm font-semibold text-gray-600 tracking-wider">Name</th>
                                    <th className="px-6 py-4 text-left text-sm font-semibold text-gray-600 tracking-wider">Description</th>
                                    <th className="px-6 py-4 text-left text-sm font-semibold text-gray-600 tracking-wider">Created At</th>
                                    <th className="px-6 py-4 text-left text-sm font-semibold text-gray-600 tracking-wider">Source</th>
                                    <th className="px-6 py-4 text-right text-sm font-semibold text-gray-600 tracking-wider">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-100">
                                {containers.map((container) => (
                                    <tr key={container.id} className="hover:bg-blue-50 transition-colors">
                                        <td className="px-6 py-4 whitespace-nowrap text-md font-semibold text-gray-900">{container.name}</td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                                            {container.description && container.description.length > 50 ? `${container.description.substring(0, 50)}...` : container.description}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                                            {new Date(container.created_at).toLocaleDateString()}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                                            {container.has_github ? (
                                                <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-bold bg-[#EAECFF] text-[#6966FF] border border-[#6966FF]">
                                                    <FaGithub /> GitHub
                                                </span>
                                            ) : (
                                                <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-gray-100 text-gray-600 border border-gray-300">
                                                    ZIP Upload
                                                </span>
                                            )}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                            <button
                                                onClick={() => openDetails(container)}
                                                className="text-[#6966FF] hover:text-blue-800 mr-4 font-bold"
                                            >
                                                Details
                                            </button>
                                            <button
                                                onClick={() => handleDelete(container.id)}
                                                className="text-red-500 hover:text-red-700 font-bold"
                                            >
                                                Delete
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                                {containers.length === 0 && (
                                    <tr>
                                        <td colSpan="5" className="px-6 py-8 text-center text-md text-gray-500">
                                            No containers found.
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                </main>
            </div>

            {/* Details Modal */}
            {isModalOpen && selectedContainer && (
                <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full flex items-center justify-center z-50">
                    <div className="relative mx-auto p-8 border w-3/4 max-w-2xl shadow-lg rounded-lg bg-white">
                        <h3 className="text-2xl font-bold text-gray-900 border-b pb-4 mb-4">Container Details</h3>

                        <div className="space-y-4 mb-6">
                            <div>
                                <span className="font-semibold text-gray-700 block">Name:</span>
                                <span className="text-gray-900">{selectedContainer.name}</span>
                            </div>
                            <div>
                                <span className="font-semibold text-gray-700 block">Description:</span>
                                <span className="text-gray-900">{selectedContainer.description}</span>
                            </div>

                            {selectedContainer.has_github && (
                                <div className="bg-gray-50 p-4 rounded-md border border-gray-200 mt-4">
                                    <h4 className="font-bold text-gray-800 mb-2 border-b pb-2 flex items-center">
                                        GitHub Synchronization
                                    </h4>
                                    <div className="grid grid-cols-1 gap-2 text-sm mt-3">
                                        <p><span className="font-semibold text-gray-600">Repository:</span> <a href={selectedContainer.github_repo_url} target="_blank" rel="noreferrer" className="text-blue-600 hover:underline">{selectedContainer.github_repo_url}</a></p>
                                        <p><span className="font-semibold text-gray-600">Folder:</span> {selectedContainer.github_folder || '/'}</p>
                                        <p><span className="font-semibold text-gray-600">Current Local Hash:</span> <code className="bg-gray-200 px-1 rounded">{selectedContainer.folder_hash?.substring(0, 7) || 'Unknown'}</code></p>

                                        {updateInfo && (
                                            <p className="mt-2 text-md">
                                                <span className="font-semibold text-gray-600">Remote Status: </span>
                                                {updateInfo.update_available ? (
                                                    <span className="text-red-600 font-bold">Out of Sync (Remote: {updateInfo.remote_hash?.substring(0, 7)})</span>
                                                ) : (
                                                    <span className="text-green-600 font-bold">Synchronized (Remote: {updateInfo.remote_hash?.substring(0, 7)})</span>
                                                )}
                                            </p>
                                        )}
                                    </div>

                                    <div className="flex gap-3 mt-4 pt-4 border-t border-gray-200">
                                        <button
                                            onClick={checkUpdate}
                                            disabled={isCheckingUpdate}
                                            className="bg-gray-200 hover:bg-gray-300 text-gray-800 font-semibold py-2 px-4 rounded flex items-center transition"
                                        >
                                            {isCheckingUpdate ? "Checking..." : "Check for Update"}
                                        </button>
                                        {updateInfo && updateInfo.update_available && (
                                            <button
                                                onClick={pullUpdate}
                                                className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded flex items-center transition"
                                            >
                                                Pull Update
                                            </button>
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>

                        <div className="flex justify-end mt-4 pt-4 border-t border-gray-200">
                            <button
                                onClick={() => setIsModalOpen(false)}
                                className="bg-gray-500 hover:bg-gray-600 text-white font-bold py-2 px-6 rounded transition duration-200"
                            >
                                Close
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default Containers;
