import os
import glob
import datetime
import moviepy.editor as mp

# 获取今天的日期
today = datetime.date.today().strftime("%Y-%m-%d")

# 构造今天日期的文件夹路径
folder_path = os.path.join(os.getcwd(), today)

# 搜索指定文件夹下的所有 .mp4 文件并按名称排序
files = glob.glob(os.path.join(folder_path, "*.mp4"))
files.sort(key=lambda x: int(x.split("-")[-1].split(".")[0]))

if len(files) < 2:
    print("文件夹内的视频文件数量不足，无法进行合并。")
else:
    # 创建一个空的 VideoClip 列表
    video_clips = []

    try:
        # 逐个加载视频文件，并添加到 VideoClip 列表中
        for file in files:
            video = mp.VideoFileClip(file)
            video_clips.append(video)

        # 使用 concatenate_videoclips() 函数合并视频
        final_video = mp.concatenate_videoclips(video_clips)

        # 输出合并后的视频文件路径
        output_path = os.path.join(os.getcwd(), "merged.mp4")

        # 保存合并后的视频文件
        final_video.write_videofile(output_path)

        print(f"视频文件合并完成！保存路径：{output_path}")

        # 删除需要合并的视频文件
        for file in files:
            os.remove(file)

    except Exception as e:
        print(f"视频文件合并失败：{e}")

# 创建 log 文件夹
log_folder = "log"
os.makedirs(log_folder, exist_ok=True)

# 创建控制台日志文件 hlog.txt，并将日志记录到文件中
log_file_path = os.path.join(log_folder, f"hlog_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt")

# 记录日志
now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
log_file = open(log_file_path, "w")
log_file.write(f"[{now}] 视频文件合并完成：{folder_path} -> {output_path}\n")
log_file.close()
