$(document).ready(function() {
    let selectedFiles = [];
    let currentTaskId = null;
    let progressChecker = null;

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

    // 处理选择的文件
    function handleFiles(files) {
        selectedFiles = Array.from(files).filter(file => file.name.endsWith('.ts'));
        updateFileList();
    }

    // 更新文件列表显示
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
        $('#uploadForm button[type="submit"]').prop('disabled', selectedFiles.length === 0);
    }

    // 删除文件
    $(document).on('click', '.remove-file', function() {
        const index = $(this).data('index');
        selectedFiles.splice(index, 1);
        updateFileList();
    });

    // 验证文件顺序
    function validateFileOrder(fileNames) {
        const numbers = fileNames.map(name => {
            const match = name.match(/(\d+)/);
            return match ? parseInt(match[1]) : null;
        }).filter(n => n !== null);
        
        for (let i = 1; i < numbers.length; i++) {
            if (numbers[i] !== numbers[i-1] + 1) {
                return false;
            }
        }
        return true;
    }

    // 上传表单处理
    $('#uploadForm').on('submit', function(e) {
        e.preventDefault();
        
        // 移除之前的错误提示
        $('.alert-danger').remove();
        
        if (selectedFiles.length === 0) {
            // 添加错误提示
            const errorAlert = $(`
                <div class="alert alert-danger alert-dismissible fade show mb-3" role="alert">
                    <i class="bi bi-exclamation-triangle-fill me-2"></i>
                    请选择要合并的TS文件
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                </div>
            `);
            $('#uploadForm').prepend(errorAlert);
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
        $('#progressSection').addClass('fade-in').show();
        $('#downloadSection').addClass('fade-in').show();
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
            xhr: function() {
                const xhr = new window.XMLHttpRequest();
                xhr.upload.addEventListener('progress', function(e) {
                    if (e.lengthComputable) {
                        const percent = Math.round((e.loaded / e.total) * 100) + '%';
                        $('#progressBar')
                            .css('width', percent)
                            .text(percent);
                        $('#statusText').text('正在上传文件...' + percent);
                    }
                }, false);
                return xhr;
            },
            success: function(response) {
                if (response.error) {
                    $('#statusText').text('上传失败: ' + response.error);
                    $('#progressBar').addClass('bg-danger');
                    $('#retryMergeBtn').show();
                    return;
                }
                currentTaskId = response.task_id;
                $('#statusText').text('文件上传完成，开始合并...');
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

    // 检查合并进度
    function startProgressCheck() {
        if (progressChecker) {
            clearInterval(progressChecker);
        }
        
        progressChecker = setInterval(function() {
            if (!currentTaskId) return;
            
            $.get('/progress/' + currentTaskId, function(data) {
                if (data.error) {
                    clearInterval(progressChecker);
                    $('#statusText').text('合并失败: ' + data.status);
                    $('#progressBar').addClass('bg-danger');
                    $('#retryMergeBtn').show();
                    return;
                }
                
                const progress = data.progress + '%';
                $('#progressBar')
                    .css('width', progress)
                    .text(progress);
                $('#statusText').text(data.status);
                
                if (data.progress >= 100) {
                    clearInterval(progressChecker);
                    $('#downloadSection').fadeIn('fast');
                    $('#downloadBtn')
                        .attr('href', '/download/' + currentTaskId)
                        .attr('title', '下载合并后的视频文件');
                    $('#progressBar').removeClass('progress-bar-animated');
                    $('#retryMergeBtn').hide();
                    
                    // 切换到视频下载功能项并刷新任务列表
                    setTimeout(() => {
                        $('a[data-function="video-download"]').click();
                        $(document).trigger('refreshTaskList');
                    }, 1000);
                }
            }).fail(function(xhr) {
                clearInterval(progressChecker);
                $('#statusText').text('检查进度失败: ' + (xhr.responseJSON?.error || '任务不存在'));
                $('#progressBar').addClass('bg-danger');
                $('#retryMergeBtn').show();
            });
        }, 1000);
    }

    // 重试按钮处理
    $('#retryMergeBtn').on('click', function() {
        if (currentTaskId) {
            $('#progressBar')
                .removeClass('bg-danger')
                .css('width', '0%')
                .text('0%');
            $('#statusText').text('重新开始合并...');
            $(this).hide();
            startProgressCheck();
        }
    });
}); 