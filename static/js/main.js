$(document).ready(function() {
    let currentTaskId = null;
    let progressChecker = null;
    let selectedFiles = [];

    // 更新时间显示
    function updateTime() {
        const now = new Date();
        const timeStr = now.toLocaleTimeString();
        $('#current-time').text(timeStr);
    }
    setInterval(updateTime, 1000);
    updateTime();

    // 侧边栏切换
    $('#sidebarCollapse').on('click', function() {
        $('#sidebar').toggleClass('active');
        $(this).find('i').toggleClass('bi-list bi-x');
    });

    // 功能切换
    $('a[data-function]').on('click', function(e) {
        e.preventDefault();
        
        // 更新活动状态
        $('a[data-function]').parent().removeClass('active');
        $(this).parent().addClass('active');
        
        // 更新标题
        $('#current-function-title').text($(this).find('span').text());
        
        // 隐藏所有功能区域
        $('.function-section').hide();
        
        // 显示选中的功能区域
        const functionId = $(this).data('function');
        $(`#${functionId}-section`).show().addClass('animate__animated animate__fadeIn');
    });

    // 文件拖放处理
    $('.upload-area').on('dragover', function(e) {
        e.preventDefault();
        $(this).addClass('drag-over');
    }).on('dragleave', function(e) {
        e.preventDefault();
        $(this).removeClass('drag-over');
    }).on('drop', function(e) {
        e.preventDefault();
        $(this).removeClass('drag-over');
        
        const files = e.originalEvent.dataTransfer.files;
        handleFiles(files);
    });

    // 文件选择处理
    $('#tsFiles').on('change', function() {
        handleFiles(this.files);
    });

    function handleFiles(files) {
        selectedFiles = Array.from(files).filter(file => file.name.endsWith('.ts'));
        updateFileList();
    }

    function updateFileList() {
        const fileList = $('#fileList');
        fileList.empty();

        selectedFiles.forEach((file, index) => {
            const fileSize = (file.size / (1024 * 1024)).toFixed(2);
            const fileItem = $(`
                <div class="file-item animate-fade">
                    <div>
                        <i class="bi bi-file-earmark-play"></i>
                        <span>${file.name}</span>
                        <span class="text-muted small">(${fileSize} MB)</span>
                    </div>
                    <i class="bi bi-x-circle remove-file" data-index="${index}"></i>
                </div>
            `);
            fileList.append(fileItem);
        });

        // 显示或隐藏提交按钮
        if (selectedFiles.length > 0) {
            $('#uploadForm button[type="submit"]').prop('disabled', false);
        } else {
            $('#uploadForm button[type="submit"]').prop('disabled', true);
        }
    }

    // 删除文件
    $(document).on('click', '.remove-file', function() {
        const index = $(this).data('index');
        selectedFiles.splice(index, 1);
        updateFileList();
    });

    // 文件上传处理
    $('#uploadForm').on('submit', function(e) {
        e.preventDefault();
        
        if (selectedFiles.length === 0) {
            alert('请选择要合并的TS文件');
            return;
        }

        // 验证文件顺序
        const fileNames = selectedFiles.map(f => f.name);
        if (!validateFileOrder(fileNames)) {
            if (!confirm('文件顺序可能不正确，是否继续？')) {
                return;
            }
        }

        const formData = new FormData();
        selectedFiles.forEach(file => {
            formData.append('files[]', file);
        });
        
        // 显示进度区域
        $('#progressSection').fadeIn();
        $('#downloadSection').hide();
        $('#progressBar')
            .removeClass('bg-danger')
            .css('width', '0%')
            .text('0%');
        $('#statusText').text('正在上传文件...');
        $('#retryMergeBtn').hide();
        
        // 发送上传请求
        $.ajax({
            url: '/upload',
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            success: function(response) {
                if (response.error) {
                    $('#statusText').text('上传失败: ' + response.error);
                    $('#progressBar').addClass('bg-danger');
                    $('#retryMergeBtn').show();
                    return;
                }
                currentTaskId = response.task_id;
                startProgressCheck();
                
                // 清空文件列表
                selectedFiles = [];
                updateFileList();
            },
            error: function(xhr) {
                $('#statusText').text('上传失败: ' + (xhr.responseJSON?.error || '未知错误'));
                $('#progressBar').addClass('bg-danger');
                $('#retryMergeBtn').show();
            }
        });
    });

    // 添加文件顺序验证函数
    function validateFileOrder(fileNames) {
        // 提取序号并排序
        const numbers = fileNames.map(name => {
            const match = name.match(/(\d+)/);
            return match ? parseInt(match[1]) : null;
        }).filter(n => n !== null);
        
        // 检查是否连续
        for (let i = 1; i < numbers.length; i++) {
            if (numbers[i] !== numbers[i-1] + 1) {
                return false;
            }
        }
        return true;
    }

    // 修改重试功能的事件处理
    $(document).on('click', '.retry-task', function(e) {
        e.preventDefault();
        const taskItem = $(this).closest('.list-group-item');
        const taskId = taskItem.data('task-id');
        
        // 先获取任务详情
        $.get(`/tasks/${taskId}/detail`, function(task) {
            const segments_info = task.segments_info || {};
            const failed_segments = Object.entries(segments_info)
                .filter(([_, info]) => info.status === 'failed' || !info.size)
                .map(([number]) => number);
            
            if (failed_segments.length > 0) {
                // 有失败的片段，提示重试下载
                if (confirm(`发现 ${failed_segments.length} 个片段下载失败，是否重试下载？`)) {
                    $.ajax({
                        url: `/tasks/${taskId}/retry`,
                        type: 'POST',
                        success: function(response) {
                            refreshTaskList();
                        },
                        error: function(xhr) {
                            alert('重试失败: ' + (xhr.responseJSON?.error || '未知错误'));
                        }
                    });
                }
            } else {
                // 所有片段都已下载，询问是否合并
                if (confirm('所有片段已下载完成，是否开始合并？')) {
                    // 显示合并进度
                    const progressHtml = `
                        <div class="merge-progress mt-2">
                            <div class="progress" style="height: 6px;">
                                <div class="progress-bar progress-bar-striped progress-bar-animated" 
                                     role="progressbar" style="width: 0%"></div>
                            </div>
                            <p class="text-center small mt-1 mb-0">准备合并...</p>
                        </div>
                    `;
                    taskItem.find('.progress-info').after(progressHtml);
                    
                    // 发送合并请求
                    $.ajax({
                        url: `/tasks/${taskId}/merge`,
                        type: 'POST',
                        success: function(response) {
                            // 开始检查合并进度
                            checkMergeProgress(taskId, taskItem);
                        },
                        error: function(xhr) {
                            taskItem.find('.merge-progress p').text('合并失败: ' + (xhr.responseJSON?.error || '未知错误'));
                            taskItem.find('.merge-progress .progress-bar').addClass('bg-danger');
                        }
                    });
                }
            }
        });
    });

    // 修改checkMergeProgress函数
    function checkMergeProgress(taskId, taskItem) {
        const progressChecker = setInterval(() => {
            $.get(`/tasks/${taskId}/merge/progress`, function(data) {
                const progress = data.progress + '%';
                taskItem.find('.merge-progress .progress-bar').css('width', progress);
                taskItem.find('.merge-progress p').text(data.status);
                
                if (data.error) {
                    clearInterval(progressChecker);
                    taskItem.find('.merge-progress .progress-bar').addClass('bg-danger');
                    return;
                }
                
                if (data.progress >= 100) {
                    clearInterval(progressChecker);
                    taskItem.find('.merge-progress').fadeOut(500, function() {
                        $(this).remove();
                        // 立即刷新任务列表以显示新按钮
                        refreshTaskList();
                    });
                }
            });
        }, 1000);
    }

    // 修改视频下载表单处理
    $('#videoDownloadForm').on('submit', function(e) {
        e.preventDefault();
        
        const pid = $('#videoPid').val().trim();
        if (!pid) return;
        
        // 验证PID格式
        if (!/^[a-f0-9]{32}$/i.test(pid)) {
            alert('请输入正确的PID格式');
            return;
        }
        
        // 清空输入框
        $('#videoPid').val('');
        
        // 发送下载请求
        $.ajax({
            url: '/video/download',
            type: 'POST',
            data: JSON.stringify({ pid: pid }),
            contentType: 'application/json',
            success: function(response) {
                // 刷新任务列表
                refreshTaskList();
                
                // 滚动到任务列表
                setTimeout(() => {
                    const taskList = $('#taskList');
                    const taskListTop = taskList.offset().top;
                    const scrollOffset = taskListTop - 100; // 留出一些顶部空间
                    
                    $('html, body').animate({
                        scrollTop: scrollOffset
                    }, {
                        duration: 800,
                        easing: 'easeInOutQuad',
                        complete: function() {
                            // 添加高亮效果
                            const newTask = taskList.find('.task-item').first();
                            newTask.addClass('task-highlight');
                            setTimeout(() => {
                                newTask.removeClass('task-highlight');
                            }, 2000);
                        }
                    });
                }, 500); // 等待任务列表刷新
            },
            error: function(xhr) {
                alert('下载失败: ' + (xhr.responseJSON?.error || '未知错误'));
            }
        });
    });

    // 修改refreshTaskList函数
    function refreshTaskList() {
        $.get('/tasks', function(tasks) {
            Object.entries(tasks).forEach(([taskId, task]) => {
                // 计算实际进度
                const segments_info = task.segments_info || {};
                const total_segments = task.total_segments || Object.keys(segments_info).length;
                const completed_segments = Object.values(segments_info)
                    .filter(info => info.status === 'completed').length;
                
                // 计算实际进度百分比
                const actual_progress = total_segments ? 
                    Math.round((completed_segments / total_segments) * 100) : 0;
                
                // 获取下载状态
                const isDownloading = task.status.includes('下载片段');
                const isCompleted = task.status === '下载完成！' || task.status === '合并完成！';
                const hasFailed = task.error;
                const hasOutputFile = task.output_file ? true : false;
                
                // 查找现有任务项
                let taskItem = $(`.task-item[data-task-id="${taskId}"]`);
                
                if (taskItem.length === 0) {
                    // 如果任务项不存在，创建新的任务项
                    const taskHtml = createTaskItemHtml(taskId, task, actual_progress, total_segments, completed_segments, isDownloading, isCompleted, hasFailed);
                    $('#taskList').append(taskHtml);
                } else {
                    // 如果任务项存在，更新标题
                    taskItem.find('.task-title').text(task.title || '《新闻联播》');
                    // 如果任务项存在，只更新需要更新的部分
                    taskItem.find('.task-status').text(task.status);
                    taskItem.find('.progress-text').text(`${actual_progress}%`);
                    taskItem.find('.progress-bar')
                        .css('width', `${actual_progress}%`)
                        .toggleClass('bg-danger', hasFailed)
                        .toggleClass('progress-bar-striped progress-bar-animated', isDownloading);
                    taskItem.find('.segments-info').html(`
                        <i class="bi bi-collection"></i> ${completed_segments}/${total_segments} 片段
                    `);
                    taskItem.find('.status-text').html(`
                        ${isDownloading ? '<i class="bi bi-arrow-down-circle"></i> 下载中' : 
                         isCompleted ? '<i class="bi bi-check-circle"></i> 完成' : 
                         hasFailed ? '<i class="bi bi-exclamation-circle"></i> 失败' : 
                         '<i class="bi bi-clock"></i> 等待中'}
                    `);
                    taskItem.find('.speed-info').html(
                        isDownloading ? '<i class="bi bi-speedometer2"></i> 计算中...' : ''
                    );

                    // 更新按钮
                    const actionsDiv = taskItem.find('.task-actions');
                    
                    if (isCompleted && hasOutputFile) {
                        // 检查是否已存在按钮
                        if (!actionsDiv.find('.preview-video').length) {
                            actionsDiv.prepend(`
                                <button class="btn btn-sm btn-outline-primary preview-video me-2" 
                                        data-bs-toggle="modal" 
                                        data-bs-target="#videoPreviewModal" 
                                        data-task-id="${taskId}"
                                        title="预览视频">
                                    <i class="bi bi-play-circle"></i>
                                </button>
                                <a href="/download/${taskId}" 
                                   class="btn btn-sm btn-success me-2" 
                                   download
                                   title="下载视频">
                                    <i class="bi bi-download"></i>
                                </a>
                            `);
                        }
                    } else {
                        // 移除预览和下载按钮
                        actionsDiv.find('.preview-video, .btn-success').remove();
                    }
                }
            });
            
            // 移除已不存在的任务
            $('.task-item').each(function() {
                const taskId = $(this).data('task-id');
                if (!tasks[taskId]) {
                    $(this).fadeOut(300, function() { $(this).remove(); });
                }
            });
        });
    }

    // 在createTaskItemHtml函数中的操作按钮部分添加预览和下载按钮
    function createTaskItemHtml(taskId, task, progress, total, completed, isDownloading, isCompleted, hasFailed) {
        return `
            <div class="list-group-item task-item" data-task-id="${taskId}">
                <div class="d-flex justify-content-between align-items-center">
                    <div class="flex-grow-1">
                        <div class="d-flex justify-content-between">
                            <h6 class="mb-1 task-title">${task.title || '《新闻联播》'}</h6>
                            <div class="task-actions">
                                ${hasFailed ? `
                                    <button class="btn btn-sm btn-outline-warning retry-task me-2" title="重试下载">
                                        <i class="bi bi-arrow-clockwise"></i>
                                    </button>
                                ` : ''}
                                ${isCompleted && task.output_file ? `
                                    <button class="btn btn-sm btn-outline-primary preview-video me-2" 
                                            data-bs-toggle="modal" 
                                            data-bs-target="#videoPreviewModal" 
                                            data-task-id="${taskId}"
                                            title="预览视频">
                                        <i class="bi bi-play-circle"></i>
                                    </button>
                                    <a href="/download/${taskId}" 
                                       class="btn btn-sm btn-success me-2" 
                                       download
                                       title="下载视频">
                                        <i class="bi bi-download"></i>
                                    </a>
                                ` : ''}
                                <button class="btn btn-sm btn-outline-danger delete-task" title="删除任务">
                                    <i class="bi bi-trash"></i>
                                </button>
                            </div>
                        </div>
                        <p class="mb-1 text-muted small task-status">${task.status}</p>
                        <div class="progress-info">
                            <div class="progress-status d-flex justify-content-between mb-1">
                                <span class="status-text">
                                    ${isDownloading ? '<i class="bi bi-arrow-down-circle"></i> 下载中' : 
                                     isCompleted ? '<i class="bi bi-check-circle"></i> 完成' : 
                                     hasFailed ? '<i class="bi bi-exclamation-circle"></i> 失败' : 
                                     '<i class="bi bi-clock"></i> 等待中'}
                                </span>
                                <span class="progress-text">${progress}%</span>
                            </div>
                            <div class="progress" style="height: 8px;">
                                <div class="progress-bar ${hasFailed ? 'bg-danger' : ''} 
                                    ${isDownloading ? 'progress-bar-striped progress-bar-animated' : ''}" 
                                    role="progressbar" 
                                    style="width: ${progress}%">
                                </div>
                            </div>
                            <div class="d-flex justify-content-between mt-1">
                                <small class="text-muted segments-info">
                                    <i class="bi bi-collection"></i> ${completed}/${total} 片段
                                </small>
                                <small class="text-muted speed-info">
                                    ${isDownloading ? '<i class="bi bi-speedometer2"></i> 计算中...' : ''}
                                </small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    // 修改任务项点击事件
    $(document).on('click', '.task-item', function(e) {
        // 如果点击的是按钮或按钮内的元素，不处理
        if ($(e.target).closest('.task-actions').length > 0) {
            return;
        }
        
        const taskId = $(this).data('task-id');
        showTaskDetail(taskId);
    });

    // 任务详情显示函数
    function showTaskDetail(taskId) {
        let updateTimer = null;

        function updateTaskDetail(task) {
            // 保存当前任务ID到删除按钮
            $('.delete-task-detail').data('task-id', taskId);
            
            // 更新基本信息
            $('#taskDetailTitle').text(task.title || '未知标题');
            $('#taskDetailCreatedAt').text(formatDate(task.created_at));
            $('#taskDetailStatus').text(task.status);
            $('#taskDetailProgress').text(task.progress + '%');
            $('#taskDetailPid').text(task.pid || '-');
            $('#taskDetailSize').text(formatSize(task.total_size || 0));
            
            // 计算总耗时
            const start_time = task.start_time;
            const is_active = !task.error && task.progress < 100;
            
            function updateDuration() {
                if (start_time) {
                    const duration = is_active ? 
                        Math.floor(Date.now() / 1000 - start_time) * 1000 :
                        task.total_duration || 0;
                    $('#taskDetailTotalDuration').text(formatTotalDuration(duration));
                }
            }
            
            // 清除之前的定时器
            if (updateTimer) {
                clearInterval(updateTimer);
                updateTimer = null;
            }
            
            // 只有活动任务才启动定时器
            if (is_active) {
                updateDuration();
                updateTimer = setInterval(updateDuration, 1000);
            } else {
                updateDuration();
            }
            
            // 更新片段信息
            updateSegmentInfo(task);
        }

        // 在模态框关闭时清理定时器
        $('#taskDetailModal').on('hidden.bs.modal', function () {
            if (updateTimer) {
                clearInterval(updateTimer);
                updateTimer = null;
            }
        });

        // 获取并显示任务详情
        $.get(`/tasks/${taskId}/detail`, function(task) {
            updateTaskDetail(task);
            
            // 显示模态框
            const modal = new bootstrap.Modal(document.getElementById('taskDetailModal'));
            modal.show();
        });
    }

    // 添加状态格式化函数
    function formatStatus(status) {
        const statusMap = {
            'completed': '完成',
            'failed': '失败',
            'downloading': '下载中',
            'waiting': '等待中'
        };
        return statusMap[status] || status;
    }

    // 辅助函数：格式化日期
    function formatDate(dateStr) {
        if (!dateStr) return '-';
        const date = new Date(dateStr);
        return date.toLocaleString();
    }

    // 辅助函数：格式化文件大小
    function formatSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // 添加鼠标悬停效果的CSS
    const style = $('<style>').text(`
        .task-item {
            cursor: pointer;
            transition: background-color 0.2s;
        }
        .task-item:hover {
            background-color: rgba(0,0,0,0.02);
        }
    `);
    $('head').append(style);

    // 添加删除任务的事件处理
    $(document).on('click', '.delete-task', function(e) {
        e.preventDefault();
        const taskItem = $(this).closest('.list-group-item');
        const taskId = taskItem.data('task-id');
        
        if (confirm('确定要删除这个任务吗？')) {
            $.ajax({
                url: `/tasks/${taskId}`,
                type: 'DELETE',
                success: function() {
                    taskItem.fadeOut(300, function() {
                        $(this).remove();
                    });
                },
                error: function() {
                    alert('删除任务失败');
                }
            });
        }
    });

    // 添加手动合并功能
    $(document).on('click', '.merge-segments', function() {
        const taskId = $(this).closest('.modal').data('task-id');
        const $mergeProgress = $('.merge-progress');
        const $progressBar = $mergeProgress.find('.progress-bar');
        const $statusText = $mergeProgress.find('p');
        
        // 显示进度条
        $mergeProgress.show();
        $progressBar.css('width', '0%');
        $statusText.text('准备合并文件...');
        
        // 发送合并请求
        $.post(`/tasks/${taskId}/merge`)
            .done(function(response) {
                // 开始检查合并进度
                const progressChecker = setInterval(function() {
                    $.get(`/tasks/${taskId}/merge/progress`, function(data) {
                        $progressBar.css('width', data.progress + '%');
                        $statusText.text(data.status);
                        
                        if (data.error) {
                            clearInterval(progressChecker);
                            $progressBar.addClass('bg-danger');
                            return;
                        }
                        
                        if (data.progress >= 100) {
                            clearInterval(progressChecker);
                            // 刷新任务列表和详情
                            refreshTaskList();
                            refreshTaskDetail(taskId);
                            // 隐藏进度条
                            setTimeout(() => {
                                $mergeProgress.fadeOut();
                            }, 1000);
                        }
                    });
                }, 1000);
            })
            .fail(function(xhr) {
                $statusText.text('合并失败: ' + (xhr.responseJSON?.error || '未知错误'));
                $progressBar.addClass('bg-danger');
            });
    });

    // 添加任务详情刷新函数
    function refreshTaskDetail(taskId) {
        $.get(`/tasks/${taskId}/detail`, function(task) {
            $('#taskDetailTitle').text(task.title || '-');
            $('#taskDetailCreatedAt').text(formatDateTime(task.created_at));
            $('#taskDetailStatus').text(task.status);
            $('#taskDetailProgress').text(task.progress + '%');
            $('#taskDetailPid').text(task.pid || '-');
            $('#taskDetailSize').text(formatFileSize(task.total_size));
            $('#taskDetailTotalDuration').text(formatDuration(task.total_duration));
            
            // 更新片段表格
            updateSegmentsTable(task.segments);
        });
    }

    // 优化性能：防抖函数
    function debounce(func, wait) {
        let timeout;
        return function(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    }

    // 使用防抖优化任务列表刷新
    const debouncedRefreshTaskList = debounce(refreshTaskList, 500);

    // 优化定时刷新
    setInterval(debouncedRefreshTaskList, 2000);

    // 优化任务详情更新
    const debouncedUpdateSegmentInfo = debounce(updateSegmentInfo, 200);

    // 添加删除按钮的点击处理
    $(document).on('click', '.delete-task-detail', function(e) {
        e.preventDefault();
        const taskId = $(this).data('task-id');
        const modal = bootstrap.Modal.getInstance(document.getElementById('taskDetailModal'));
        
        if (confirm('确定要删除这个任务吗？')) {
            $.ajax({
                url: `/tasks/${taskId}`,
                type: 'DELETE',
                success: function() {
                    // 关闭模态框
                    modal.hide();
                    // 从任务列表中移除任务项
                    $(`.task-item[data-task-id="${taskId}"]`).fadeOut(300, function() {
                        $(this).remove();
                    });
                },
                error: function() {
                    alert('删除任务失败');
                }
            });
        }
    });

    // 添加单个片段重试的事件处理
    $(document).on('click', '.retry-segment', function(e) {
        e.stopPropagation();
        const segmentNumber = $(this).data('segment');
        const taskId = $('.delete-task-detail').data('task-id');
        
        if (confirm(`确定要重试第 ${segmentNumber} 个片段吗？`)) {
            $.ajax({
                url: `/tasks/${taskId}/segments/${segmentNumber}/retry`,
                type: 'POST',
                success: function(response) {
                    // 刷新任务详情
                    $.get(`/tasks/${taskId}/detail`, function(updatedTask) {
                        updateSegmentInfo(updatedTask);
                    });
                },
                error: function(xhr) {
                    alert('重试失败: ' + (xhr.responseJSON?.error || '未知错误'));
                }
            });
        }
    });

    // 添加格式化总耗时的函数
    function formatTotalDuration(ms) {
        if (!ms) return '-';
        
        const seconds = Math.floor(ms / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        
        if (hours > 0) {
            const remainingMinutes = minutes % 60;
            const remainingSeconds = seconds % 60;
            return `${hours}小时${remainingMinutes}分${remainingSeconds}秒`;
        } else if (minutes > 0) {
            const remainingSeconds = seconds % 60;
            return `${minutes}分${remainingSeconds}秒`;
        } else if (seconds > 0) {
            return `${seconds}秒`;
        } else {
            return `${ms}毫秒`;
        }
    }

    // 添加格式化片段耗时的函数
    function formatSegmentDuration(ms) {
        if (!ms) return '-';
        return `${ms}ms`;
    }

    // 修改updateSegmentInfo函数
    function updateSegmentInfo(task) {
        const segmentsBody = $('#taskDetailSegments');
        const segments_info = task.segments_info || {};
        
        Object.entries(segments_info).forEach(([number, info]) => {
            const status = info.status;
            const size = info.size || 0;
            const duration = info.duration;  // 单个片段下载耗时
            const start_time = info.start_time;
            
            // 计算实时耗时（仅对正在下载的片段）
            let currentDuration = duration;
            if (status === 'downloading' && start_time) {
                currentDuration = Math.floor((Date.now() / 1000 - start_time) * 1000);
            }
            
            // 更新或创建行
            let row = segmentsBody.find(`tr[data-segment="${number}"]`);
            if (row.length === 0) {
                row = $(`
                    <tr data-segment="${number}">
                        <td>${number}</td>
                        <td>
                            <span class="badge ${
                                status === 'completed' ? 'bg-success' : 
                                status === 'failed' ? 'bg-danger' : 
                                status === 'waiting' ? 'bg-secondary' :
                                'bg-warning'
                            }">
                                ${formatStatus(status)}
                            </span>
                            ${status === 'failed' ? `
                                <button class="btn btn-sm btn-link retry-segment p-0 ms-2" 
                                        data-segment="${number}">
                                    <i class="bi bi-arrow-clockwise text-warning"></i>
                                </button>
                            ` : ''}
                        </td>
                        <td>${formatSize(size)}</td>
                        <td class="duration-cell">${formatSegmentDuration(currentDuration)}</td>
                    </tr>
                `);
                segmentsBody.append(row);
            } else {
                // 更新现有行
                row.find('td:nth-child(2)').html(`
                    <span class="badge ${
                        status === 'completed' ? 'bg-success' : 
                        status === 'failed' ? 'bg-danger' : 
                        status === 'waiting' ? 'bg-secondary' :
                        'bg-warning'
                    }">
                        ${formatStatus(status)}
                    </span>
                    ${status === 'failed' ? `
                        <button class="btn btn-sm btn-link retry-segment p-0 ms-2" 
                                data-segment="${number}">
                            <i class="bi bi-arrow-clockwise text-warning"></i>
                        </button>
                    ` : ''}
                `);
                row.find('td:nth-child(3)').text(formatSize(size));
                row.find('.duration-cell').text(formatSegmentDuration(currentDuration));
            }
        });
    }

    // 添加视频预览模态框的事件处理
    $(document).on('click', '.preview-video', function() {
        const taskId = $(this).data('task-id');
        const videoPlayer = $('#videoPreviewPlayer');
        videoPlayer.attr('src', `/preview/${taskId}`);
        
        // 当模态框关闭时停止视频播放
        $('#videoPreviewModal').on('hidden.bs.modal', function () {
            videoPlayer[0].pause();
            videoPlayer.attr('src', '');
        });
    });

    // 添加startProgressCheck函数
    function startProgressCheck() {
        if (progressChecker) {
            clearInterval(progressChecker);
        }
        
        progressChecker = setInterval(function() {
            if (!currentTaskId) return;
            
            $.get('/progress/' + currentTaskId, function(data) {
                const progress = data.progress + '%';
                $('#progressBar')
                    .css('width', progress)
                    .text(progress);
                $('#statusText').text(data.status);
                
                if (data.error) {
                    clearInterval(progressChecker);
                    $('#progressBar').addClass('bg-danger');
                    $('#retryMergeBtn').show();
                    return;
                }
                
                if (data.progress >= 100) {
                    clearInterval(progressChecker);
                    $('#downloadSection').fadeIn();
                    $('#downloadBtn')
                        .attr('href', '/download/' + currentTaskId)
                        .attr('title', '下载合并后的视频文件');
                    $('#progressBar').removeClass('progress-bar-animated');
                    $('#retryMergeBtn').hide();
                    
                    // 切换到视频下载功能项并刷新任务列表
                    setTimeout(() => {
                        $('a[data-function="video-download"]').click();
                        refreshTaskList();
                    }, 1000);
                }
            });
        }, 1000);
    }

    // 监听来自ts-merger.js的刷新请求
    $(document).on('refreshTaskList', function() {
        refreshTaskList();
    });
}); 