import openai, httplib2, time, random, textwrap, os, concurrent.futures, json, re, shutil, http.client, collections, sys, keyboard, subprocess, requests

from glob import glob
from Levenshtein import distance
from gradio_client import Client
from youtube_upload.client import YoutubeUploader
from PIL import Image, ImageDraw, ImageFont, ImageOps, UnidentifiedImageError
from rembg import remove
from joblib import Parallel, delayed
from threading import Thread
from ahk import AHK
from num2words import num2words
from roman import fromRoman
from bs4 import BeautifulSoup, NavigableString
from itertools import groupby

GPT_URL = "https://api.openai.com/v1/chat/completions"

Image.MAX_IMAGE_PIXELS = None  

CHUNK_LENGTH = 15
HELP_INFO = "lorem"

accented_to_unaccented = {
    'á': 'a', 'à': 'a', 'â': 'a', 'ä': 'a', 'ã': 'a', 'å': 'a', 'ā': 'a',
    'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e', 'ē': 'e', 'ę': 'e', 'ě': 'e',
    'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i', 'ī': 'i', 'į': 'i', 'ǐ': 'i',
    'ó': 'o', 'ò': 'o', 'ô': 'o', 'ö': 'o', 'õ': 'o', 'ø': 'o', 'ō': 'o', 'ő': 'o',
    'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u', 'ū': 'u', 'ů': 'u', 'ű': 'u',
    'ý': 'y', 'ÿ': 'y',
    'ç': 'c', 'ć': 'c', 'č': 'c',
    'ñ': 'n', 'ń': 'n', 'ň': 'n',
    'š': 's', 'ś': 's', 'ß': 'ss',
    'ž': 'z', 'ź': 'z', 'ż': 'z',
    'ł': 'l', 'ľ': 'l', 'ĺ': 'l',
    'ř': 'r',
    'đ': 'd',
    'þ': 'th',
    'ħ': 'h',
    'Á': 'A', 'À': 'A', 'Â': 'A', 'Ä': 'A', 'Ã': 'A', 'Å': 'A', 'Ā': 'A',
    'É': 'E', 'È': 'E', 'Ê': 'E', 'Ë': 'E', 'Ē': 'E', 'Ę': 'E', 'Ě': 'E',
    'Í': 'I', 'Ì': 'I', 'Î': 'I', 'Ï': 'I', 'Ī': 'I', 'Į': 'I', 'Ǐ': 'I',
    'Ó': 'O', 'Ò': 'O', 'Ô': 'O', 'Ö': 'O', 'Õ': 'O', 'Ø': 'O', 'Ō': 'O', 'Ő': 'O',
    'Ú': 'U', 'Ù': 'U', 'Û': 'U', 'Ü': 'U', 'Ū': 'U', 'Ů': 'U', 'Ű': 'U',
    'Ý': 'Y', 'Ÿ': 'Y',
    'Ç': 'C', 'Ć': 'C', 'Č': 'C',
    'Ñ': 'N', 'Ń': 'N', 'Ň': 'N',
    'Š': 'S', 'Ś': 'S',
    'Ž': 'Z', 'Ź': 'Z', 'Ż': 'Z',
    'Ł': 'L', 'Ľ': 'L', 'Ĺ': 'L',
    'Ř': 'R',
    'Đ': 'D',
    'Þ': 'TH',
    'Ħ': 'H'
}

def create_randomized_music_file(input_music_directory, output_file):
    music_files = [f for f in os.listdir(input_music_directory) if f.endswith('mp3')]
    random.shuffle(music_files)
    rand_str = str(random.randint(1000000000000, 9000000000000))
    temp_file = 'temp_' + rand_str + '.txt'
    temp_file_path = os.path.join(input_music_directory, temp_file)
    with open(temp_file_path, 'w', encoding='utf8') as f_out:
        for f in music_files[:min(20, len(music_files))]:
            f_out.write(f'file {f}\n')
    cmd = ["ffmpeg", "-f", "concat", "-i", temp_file_path, "-c", "copy", output_file]
    subprocess.run(cmd)
    os.remove(temp_file_path)

def get_music_files(music_directory):
    music_arr = []
    for root, _, files in os.walk(music_directory):
        for filename in files:
            if filename.endswith('mp3'):
                music_arr.append(os.path.join(root, filename))
    return music_arr

def merge_music_with_voice(input_file, output_dir):
    input_file_base_name = os.path.splitext(os.path.basename(input_file))[0]
    output_filename = f'{input_file_base_name}_mixed{os.path.splitext(os.path.basename(input_file))[1]}'
    output_file = os.path.join(os.path.dirname(input_file), output_filename)
    output_directory = output_dir if output_dir else os.path.dirname(input_file)
    if output_filename not in os.listdir(output_directory):
        create_randomized_music_file(MUSIC_LIB, output_file)
    combined_file = os.path.join(output_directory, input_file_base_name + '_combined.mp3')
    ffmpeg_cmd = [ "ffmpeg", "-y", "-i", input_file, "-i", output_file, "-filter_complex", "[0:a]volume=1[a1];[1:a]volume=0.25[a2];[a1][a2]amix=inputs=2:duration=first[aout]", "-map", "[aout]", combined_file ]
    subprocess.run(ffmpeg_cmd)
    
def split_video_into_chunks(input_file, output_dir):
    input_file_base_name = os.path.splitext(os.path.basename(input_file))[0]          
    output_filename = f'{input_file_base_name}_chunk_%d.mp4'
    output_path = os.path.join(output_dir if output_dir else os.path.dirname(input_file), output_filename)
    cmd = f'ffmpeg -i "{input_file}" -an -c:v copy -reset_timestamps 1 -map 0 -f segment -segment_time {CHUNK_LENGTH} "{output_path}"'
    subprocess.run(cmd, shell=True)

def operation_queue_function(q, task_function):
    while q:
        arguments = q.popleft()
        task_function(*arguments)

def get_media_duration(file_path):
    cmd = ["ffprobe", "-v", "error","-show_entries", "format=duration","-of", "default=noprint_wrappers=1:nokey=1",file_path]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except subprocess.CalledProcessError:
        return -1
        
def add_fade_in_fade_out(input_file, output_dir):
    input_file_base_name = os.path.splitext(os.path.basename(input_file))[0]      
    if input_file_base_name.endswith('fadeinfadeout'):
        return    
    output_filename = f'{input_file_base_name}_fadeinfadeout.mp4'
    output_path = os.path.join(output_dir if output_dir else os.path.dirname(input_file), output_filename)
    duration = get_media_duration(input_file)
    ffmpeg_cmd = f'ffmpeg -i {input_file} -c:v h264_nvenc -preset fast -vf "fade=t=in:st=0:d=1,fade=t=out:st={duration-2}:d=1" -an {output_path}'
    subprocess.run(ffmpeg_cmd, shell=True)
    os.remove(input_file)

def parallel_batch_task(parallel_thread_count, batch_input_directory, batch_output_directory, condition_function, task_function):
    q = collections.deque()
    for root, _, files in os.walk(batch_input_directory):
        for filename in files:
            if condition_function(filename):
                q.append((os.path.join(root, filename), batch_output_directory if batch_output_directory else root))
    with concurrent.futures.ThreadPoolExecutor() as executor:
        for _ in range(parallel_thread_count):
            executor.submit(operation_queue_function, q, task_function)

def replace_with_combined(directory):
    for root, _, files in os.walk(directory):
        for filename in files:
            if filename.endswith('.mp3') and not filename.endswith('combined.mp3'):
                os.remove(os.path.join(root, filename))
    for root, _, files in os.walk(directory):
        for filename in files:
            if filename.endswith('combined.mp3'):
                os.rename(os.path.join(root, filename), os.path.join(root, filename.replace("_combined.mp3", ".mp3")))
                
def combine_videos(source_dir, video_dir):
    def get_media_duration(file_path):
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            file_path
        ]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=True)
            return float(result.stdout.strip())
        except subprocess.CalledProcessError:
            return -1
        
    def get_random_and_video_duration(video_chunks):
        random.shuffle(video_chunks)
        for chunk in video_chunks:
            duration = get_media_duration(chunk)
            if duration > 0:
                return duration, chunk
        print("All video chunks appear to be corrupted.")
        return 0, None
    
    def get_video_chunks(video_dir):
        return [os.path.join(video_dir, f) for f in os.listdir(video_dir) if f.endswith('.mp4')]
    
    def combine_videos(videos, output_path):
        temp_file = os.path.join(os.path.dirname(output_path), "temp_list.txt")
        with open(temp_file, "w", encoding='utf8') as f:
            for vid in videos:
                f.write(f"file '{os.path.abspath(vid)}'\n")
        cmd = ["ffmpeg", "-y", "-an", "-f", "concat", "-safe", "0", "-i", temp_file, "-c", "copy", output_path]
        try:
            with open(os.devnull, 'w') as fnull:
                subprocess.run(cmd, stderr=fnull, check=True)
        except subprocess.CalledProcessError:
            print(f"Error while concatenating videos to {output_path}")
            return
        os.remove(temp_file)

    def combine_audio_video(video_path, audio_path, output_path):
        cmd = ["ffmpeg", "-i", video_path, "-i", audio_path, "-c:v", "copy", "-c:a", "aac", output_path]
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError:
            print(
                f"Error combining audio from {audio_path} with video from {video_path}")
            return
        
    def process_mp3(args):
        mp3_path, video_chunks = args
        base_name = os.path.basename(mp3_path)
        mp3_duration = get_media_duration(mp3_path)
        if mp3_duration == -1:
            print(f"Error processing {mp3_path}. Skipping...")
            return
        selected_chunks = []
        total_video_duration = 0
        print(f"Processing {mp3_path}...")
        while total_video_duration < mp3_duration:
            chunk_duration, valid_chunk = get_random_and_video_duration(
                video_chunks[:])
            if not valid_chunk:
                print(
                    f"Couldn't process {mp3_path} due to lack of valid video chunks.")
                return
            # This allows the video to be a bit longer than the audio
            if total_video_duration + chunk_duration <= mp3_duration + chunk_duration:
                selected_chunks.append(valid_chunk)
                total_video_duration += chunk_duration
                percentage_done = (total_video_duration / mp3_duration) * 100
                print(f"{percentage_done:.2f}% of {os.path.basename(mp3_path)} processed.")
            else:
                break
        if not selected_chunks:
            print(f"No valid video chunks for {mp3_path}. Skipping...")
            return
        # Combine selected video chunks
        video_without_audio_path = os.path.join(os.path.dirname(
            mp3_path), os.path.basename(mp3_path).replace('.mp3', '_temp_video.mp4'))
        combine_videos(selected_chunks, video_without_audio_path)
        print(f"Combining video chunks for {os.path.basename(mp3_path)}...")
        print(f"Finished processing {os.path.basename(mp3_path)}!")
        # Combine audio and video
        final_video_path = os.path.join(os.path.dirname(
            mp3_path), os.path.basename(mp3_path).replace('.mp3', '_video.mp4'))
        combine_audio_video(video_without_audio_path, mp3_path, final_video_path)
        print(f"Generating final video for {os.path.basename(mp3_path)}...")
        # Remove the temporary video
        os.remove(video_without_audio_path)
        print(f"Finished processing {os.path.basename(mp3_path)}!")
        
    def combiner(source_dir, video_dir):
        video_chunks = get_video_chunks(video_dir)
        all_mp3s = [os.path.join(subdir, file) for subdir, _, files in os.walk(
            source_dir) for file in files if file.endswith('.mp3')]
        Parallel(n_jobs=-1)(delayed(process_mp3)((mp3, video_chunks))
                            for mp3 in all_mp3s)
    combiner(source_dir, video_dir)

def process_directory(folder_name, google_client, google_secret, auth=True):
    uploader = YoutubeUploader(google_client, google_secret)
    if auth:
        uploader.authenticate()
    for subdir, _, files in os.walk(folder_name):
        if 'thumbnail.png' in files and any(file.endswith('.mp4') for file in files):
            paths = {name: os.path.join(subdir, name + '.txt') for name in ['title', 'tags', 'desc', 'category']}
            video_path = next(os.path.join(subdir, file) for file in files if file.endswith('.mp4'))
            thumbnail_path = os.path.join(subdir, 'thumbnail.png')
            data = {}
            for name, path in paths.items():
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf8') as f:
                        data[name] = f.read().strip()
                else:
                    if name == 'desc':
                        data[name] = ''  
                    elif name == 'category':
                        data[name] = '27'
            # Tags
            original_tags = data['tags']
            tags_list = original_tags.split(',')
            def clean_tag(tag):
                if 'school' in tag or 'ecole' in tag:
                    return 'soundfables'
                cleaned_tag = re.sub(r'[^\w\s]', '', tag)
                return f'{cleaned_tag}' if ' ' in cleaned_tag else cleaned_tag
            tags_list = [clean_tag(tag) for tag in tags_list]
            while sum(len(tag) for tag in tags_list) + len(tags_list) - 1 > 500:
                tags_list.pop()
            data['tags'] = ','.join(tags_list)
            # Title, Description, Category
            for key in ['title', 'desc', 'category']:
                data[key] = clean_tag(data.get(key, ''))
            # Ensure the title, description, and category are within expected lengths
            data['title'] = data['title'][:100]  # Assuming 100 characters is max length for title
            data['desc'] = data['desc'][:5000]  # Assuming 5000 characters is max length for description
            data['category'] = data['category'][:27]  # Assuming 27 characters is max length for category
            options = {
                "title" : data['title'], 
                "description" : data.get('desc', ''), 
                "tags" : data['tags'],
                "categoryId" : data.get('category', '27'),
                "privacyStatus" : "private", 
                "kids" : False, 
                "thumbnailLink" : thumbnail_path 
            }
            print(options)
            uploader.upload(video_path, options) 
            uploader.close()


def sanitize_title(title):
    new_title = ''
    for c in title:
        if ord('a') <= ord(c) <= ord('z') or c.isnumeric() or ord('A') <= ord(c) <= ord('Z'):
            new_title += c.lower()
        elif c in accented_to_unaccented:
            new_title += accented_to_unaccented[c].lower()
        elif new_title and new_title[-1] != '_':
            new_title += '_'
    return title.strip('_')

def sanitize_filename(fname, src_ext):
    name = ''
    if fname.endswith(src_ext):
        name = fname[:len(fname)-len(src_ext)-1]
    else:
        name = fname.split('.')[0]
    new_name = ''
    for c in name:
        if ord('a') <= ord(c) <= ord('z') or c.isnumeric() or ord('A') <= ord(c) <= ord('Z'):
            new_name += c.lower()
        elif c in accented_to_unaccented:
            new_name += accented_to_unaccented[c].lower()
        elif new_name and new_name[-1] != '_':
            new_name += '_'
    sanitized_name = new_name.strip('_')
    new_arr = sanitized_name.split('_')
    if src_ext == 'json' and new_arr[-1] == 'info':
        new_arr.pop()
        sanitized_name = '_'.join(new_arr)
    if src_ext == 'mp3' and new_arr[0] == 'output':
        new_arr[0] = ''
        sanitized_name = '_'.join(new_arr)
    if src_ext == 'mp3' and new_arr[-1].isnumeric():
        new_arr.pop()
        sanitized_name = '_'.join(new_arr)
    files_in_directory = set(os.listdir(os.getcwd()))
    k = 0
    while sanitized_name in files_in_directory and sanitized_name + '_' + str(k) in files_in_directory:
        k += 1
    sanitized_name = (sanitized_name + ('_' + str(k) if k > 0 else '')).strip('_')
    sanitized_ext = '.' + src_ext
    return sanitized_name + sanitized_ext

def random_renamer(filename):
    return str(random.randint(1000000000000000, 9999999999999999)) + ('.' + filename.split('.')[-1] if filename.split('.')[-1] else '')

def replace_renamer(filename, a, b):
    return (filename.split('.')[0].replace(a, b) if a != '*' else b) + ('.' + filename.split('.')[-1] if filename.split('.')[-1] else '')

def general_rename(target_dir, rename_function, rename_condition, replaced="", number_if_found=False):
    target_files = [os.path.join(target_dir, f) for f in os.listdir(target_dir) if rename_condition]
    for found_file in target_files:
        old_path = found_file
        new_path = rename_function(found_file)
        if number_if_found and os.path.exists(new_path):
            counter = 1
            base_new_path, ext = os.path.splitext(new_path)
            while os.path.exists(f"{base_new_path}_{counter}{ext}"):
                counter += 1
            new_path = f"{base_new_path}_{counter}{ext}"
        os.rename(old_path, os.path.join(target_dir, new_path))


def is_valid_image(img_path):
    """Returns True if the image can be opened with PIL, else False."""
    try:
        img = Image.open(img_path)
        img.close()  # Close the opened image to free up resources.
        return True
    except UnidentifiedImageError:
        return False

def process_images(content_folder, bg_folder, layer_folder):
    # Ensure valid images from both folders
    layer_images = [f for f in os.listdir(layer_folder) if f.lower().endswith(
        ('.png', '.jpg', '.jpeg')) and is_valid_image(os.path.join(layer_folder, f))]
    bg_images = [f for f in os.listdir(bg_folder) if f.lower().endswith(
        ('.png', '.jpg', '.jpeg')) and is_valid_image(os.path.join(bg_folder, f))]

    for target_dir in [dirpath for dirpath, _, filenames in os.walk(content_folder) if 'title.txt' in filenames]:
        '''if any(fname.startswith('thumbnail.') for fname in os.listdir(target_dir)):
            continue'''

        # Choose a random background image
        bg_image_file = random.choice(bg_images)
        bg_img_path = os.path.join(bg_folder, bg_image_file)

        try:
            bg_img = Image.open(bg_img_path)
        except OSError:
            print(f"Error opening image: {bg_img_path}. Skipping...")
            bg_images.remove(bg_image_file)
            continue

        # Choose a random layer image and remove its background
        layer_image_file_1 = random.choice(layer_images)
        # layer_image_file_2 = random.choice(layer_images)
        layer_img_path_1 = os.path.join(layer_folder, layer_image_file_1)
        # layer_img_path_2 = os.path.join(layer_folder, layer_image_file_2)

        try:
            layer_img_1 = Image.open(layer_img_path_1)
            layer_img_no_bg_1 = remove(layer_img_1)
        except Exception as e:
            print(
                f"Error processing layer image: {layer_img_path_1}. Reason: {e}. Skipping...")
            layer_images.remove(layer_image_file_1)
            continue

        # Integrate the background and layer here
        aspect_ratio = bg_img.width / bg_img.height
        if aspect_ratio < 1280 / 720:
            bg_img = bg_img.resize((1280, int(1280 / aspect_ratio)))
        else:
            bg_img = bg_img.resize((int(720 * aspect_ratio), 720))

        bg_img = ImageOps.fit(bg_img, (1280, 720), method=0,bleed=0.0, centering=(0.5, 0.5))

        # Add the layer on the thumbnail
        aspect_ratio_layer_1 = layer_img_no_bg_1.width / layer_img_no_bg_1.height
        # aspect_ratio_layer_2 = layer_img_no_bg_2.width / layer_img_no_bg_2.height

        if aspect_ratio_layer_1 > 1:
            new_width = bg_img.width
            new_height = int(new_width / aspect_ratio_layer_1)
        else:
            new_height = bg_img.height
            new_width = int(new_height * aspect_ratio_layer_1)
        layer_img_resized_1 = layer_img_no_bg_1.resize(
            (new_width, new_height), Image.LANCZOS)
        position = (0,
                    (bg_img.height - new_height) // 2)
        bg_img.paste(layer_img_resized_1, position, layer_img_resized_1)

        # Add title on the thumbnail
        with open(os.path.join(target_dir, 'title.txt'), 'r', encoding="utf8") as f_in:
            title = f_in.read().strip()
            d = ImageDraw.Draw(bg_img)
            fnt = ImageFont.truetype('.\\fonts\\Raleway-Bold.ttf', 70)
            wrapped_text = textwrap.wrap(title, width=30)
            total_height = len(wrapped_text) * 100
            y_start = (bg_img.height - total_height) * 0.9
            padding = 10

            for line in wrapped_text:
                dummy_img = Image.new('RGB', (1280, 720))
                dummy_draw = ImageDraw.Draw(dummy_img)
                dummy_draw.text((0, 0), line, font=fnt)
                text_width, text_height = dummy_img.getbbox()[
                    2], dummy_img.getbbox()[3]
                x = (bg_img.width - text_width) / 2
                y = y_start
                d.rounded_rectangle([x - padding, y - padding, x + text_width +
                                    padding, y + text_height + padding], fill="black", radius=10)
                d.text((x, y), line, font=fnt, fill=(255, 255, 0))
                y_start += 100

        new_path = os.path.join(
            target_dir, 'thumbnail.' + bg_image_file.split('.')[-1])
        bg_img.save(new_path)
        print(f'thumbnail saved at: {target_dir}')

def work_on_pics(output_folder, bg_folder, layer_folder):
    # Ensure valid images from both folders
    bg_images = [f for f in os.listdir(bg_folder) if f.lower().endswith(
        ('.png', '.jpg', '.jpeg')) and is_valid_image(os.path.join(bg_folder, f))]
    layer_images = [f for f in os.listdir(layer_folder) if f.lower().endswith(
        ('.png', '.jpg', '.jpeg')) and is_valid_image(os.path.join(layer_folder, f))]

    for i in range(1000000):
        # Choose a random background image
        bg_image_file = random.choice(bg_images)
        bg_img_path = os.path.join(bg_folder, bg_image_file)
        try:
            bg_img = Image.open(bg_img_path)
        except OSError:
            print(f"Error opening image: {bg_img_path}. Skipping...")
            bg_images.remove(bg_image_file)
            continue
        # Choose a random layer image and remove its background
        layer_image_file_1 = random.choice(layer_images)
        layer_image_file_2 = random.choice(layer_images)
        layer_img_path_1 = os.path.join(layer_folder, layer_image_file_1)
        layer_img_path_2 = os.path.join(layer_folder, layer_image_file_2)
        try:
            layer_img_1 = Image.open(layer_img_path_1)
            layer_img_no_bg_1 = remove(layer_img_1)
        except Exception as e:
            print(
                f"Error processing layer image: {layer_img_path_1}. Reason: {e}. Skipping...")
            layer_images.remove(layer_image_file_1)
            continue
        try:
            layer_img_2 = Image.open(layer_img_path_2)
            layer_img_no_bg_2 = remove(layer_img_2)
        except Exception as e:
            print(
                f"Error processing layer image: {layer_img_path_2}. Reason: {e}. Skipping...")
            layer_images.remove(layer_image_file_2)
            continue
        # Integrate the background and layer here
        aspect_ratio = bg_img.width / bg_img.height
        if aspect_ratio < 1280 / 720:
            bg_img = bg_img.resize((1280, int(1280 / aspect_ratio)))
        else:
            bg_img = bg_img.resize((int(720 * aspect_ratio), 720))

        bg_img = ImageOps.fit(bg_img, (1280, 720), method=0,bleed=0.0, centering=(0.5, 0.5))
        # Add the layer on the thumbnail
        aspect_ratio_layer_1 = layer_img_no_bg_1.width / layer_img_no_bg_1.height
        aspect_ratio_layer_2 = layer_img_no_bg_2.width / layer_img_no_bg_2.height
        if aspect_ratio_layer_1 > 1:
            new_width = bg_img.width
            new_height = int(new_width / aspect_ratio_layer_1)
        else:
            new_height = bg_img.height
            new_width = int(new_height * aspect_ratio_layer_1)
        layer_img_resized_1 = layer_img_no_bg_1.resize(
            (new_width, new_height), Image.LANCZOS)
        position = (0,
                    (bg_img.height - new_height) // 2)
        bg_img.paste(layer_img_resized_1, position, layer_img_resized_1)

        if aspect_ratio_layer_2 > 1:
            new_width = bg_img.width
            new_height = int(new_width / aspect_ratio_layer_2)
        else:
            new_height = bg_img.height
            new_width = int(new_height * aspect_ratio_layer_2)
        layer_img_resized_2 = layer_img_no_bg_2.resize(
            (new_width, new_height), Image.LANCZOS)
        position = ((bg_img.width) * 2 // 3,
                    (bg_img.height - new_height) // 2)
        bg_img.paste(layer_img_resized_2, position, layer_img_resized_2)

        new_path = os.path.join(
            output_folder, 'thumbnail_' + str(random.randint(1000000000000, 9999999999999)) + '.' + bg_image_file.split('.')[-1])
        bg_img.save(new_path)
        print(f'thumbnail saved at: {output_folder}')

def create_thumbnail(folder_name, image_folder):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_path = os.path.join(script_dir, folder_name)
    title_files = [dirpath for dirpath, _, filenames in os.walk(base_path) if 'title.txt' in filenames]
    image_files = [f for f in os.listdir(image_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    valid_images = [f for f in image_files if is_valid_image(os.path.join(image_folder, f))]

    for target_dir in title_files:
        # Check if thumbnail already exists, skip if it does
        '''if any(fname.startswith('thumbnail.') for fname in os.listdir(target_dir)):
            continue'''

        image_file = random.choice(valid_images)
        img_path = os.path.join(image_folder, image_file)
        
        try:
            img = Image.open(img_path)
        except OSError:
            print(f"Error opening image: {img_path}. Skipping...")
            valid_images.remove(image_file)  # Remove the invalid image from the list
            continue

        aspect_ratio = img.width / img.height
        if img.width / img.height < 1280 / 720:
            img = img.resize((1280, int(1280 / aspect_ratio)))
        else:
            img = img.resize((int(720 * aspect_ratio), 720))
        
        img = ImageOps.fit(img, (1280, 720), method=0, bleed=0.0, centering=(0.5, 0.5))

        with open(os.path.join(target_dir, 'title.txt'), 'r', encoding="utf8") as f_in:
            title = f_in.read().strip()
            d = ImageDraw.Draw(img)
            fnt = ImageFont.truetype('.\\fonts\\Raleway-Bold.ttf', 75)
            wrapped_text = textwrap.wrap(title, width=30)  # Adjust the width to fit your needs
            total_height = len(wrapped_text) * 100  # 100 is the font size
            y_start = (img.height - total_height) * 0.85
            padding = 10  # Adjust this value to increase or decrease padding

            for line in wrapped_text:
                dummy_img = Image.new('RGB', (1280, 720))
                dummy_draw = ImageDraw.Draw(dummy_img)
                dummy_draw.text((0,0), line, font=fnt)
                text_width, text_height = dummy_img.getbbox()[2], dummy_img.getbbox()[3]  # Get the width and height
                x = (img.width - text_width) / 2
                y = y_start
                d.rounded_rectangle([x - padding, y - padding, x + text_width + padding, y + text_height + padding], fill="black", radius=10)
                d.text((x, y), line, font=fnt, fill=(255, 255, 0))
                y_start += 100

            new_path = os.path.join(target_dir, 'thumbnail.' + image_file.split('.')[-1])
            img.save(new_path)
            print(f'thumbnail saved at: {target_dir}')

def bg_remover(folder_name):
    # walk through the folder to get the subfolders
    for subdir, dirs, files in os.walk(folder_name):
        # check each file in the subfolder
        for file in files:
            if file.endswith(".jpeg") or file.endswith(".jpg"):
                input_path = os.path.join(subdir, file)
                output_path = os.path.join(subdir, "output_" + file)
                input_img = Image.open(input_path)
                # Removing the background from the given Image
                output_img = remove(input_img)
                # Saving the image in the given path
                output_img.save(output_path.split('.')[0]+ '_' + str(random.randint(1000,9999)) + '.png')

def overlayer(folder_name):
    # walk through the folder to get the subfolders
    for subdir, dirs, files in os.walk(folder_name):
        # check each file in the subfolder
        for file in files:
            if file.startswith("output_"):
                person_img_path = os.path.join(subdir, file)
                thumbnail_path = os.path.join(subdir, "new_thumbnail.png")
                # Open both images
                person_img = Image.open(person_img_path)
                thumbnail = Image.open(thumbnail_path)

                # Calculate aspect ratio of person image
                aspect_ratio = person_img.width / person_img.height
                # Determine new dimensions
                if aspect_ratio > 1:
                    # Image is wide
                    new_width = thumbnail.width
                    new_height = int(new_width / aspect_ratio)
                else:
                    # Image is tall or square
                    new_height = thumbnail.height
                    new_width = int(new_height * aspect_ratio)

                # Resize person image
                person_img_resized = person_img.resize((new_width, new_height), Image.LANCZOS)

                # Calculate position to align person image to the left and center vertically
                position = (0, (thumbnail.height - new_height) // 2)

                # Paste person image onto thumbnail (assuming the person image has a transparent background)
                thumbnail.paste(person_img_resized, position, person_img_resized)
                # Save result
                thumbnail.save(os.path.join(subdir, file.split('.')[0] + "_thumbnail.png"))


def calculate_similarity(name1, name2):
    tokens1 = set(name1.split('.')[0].replace(
        "_", " ").replace("-", " ").split())
    tokens2 = set(name2.split('.')[0].replace(
        "_", " ").replace("-", " ").split())
    common_tokens = tokens1.intersection(tokens2)
    score = len(common_tokens) / max(len(tokens1), len(tokens2))
    return score

def calculate_similarity_lev(name1, name2):
    distance = distance(name1.split('.')[0], name2.split('.')[0])
    similarity = 1 - (distance / max(len(name1), len(name2)))
    return similarity

def get_handled_media_duration(file_path):
    # Using ffprobe
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=True)
        duration_str = result.stdout.strip()
        if duration_str != 'N/A':
            return float(duration_str)
        else:
            pass
    except (subprocess.CalledProcessError, ValueError):
        pass  # Silently catch the error and move on to ffmpeg method.
    return -1

def process_videos(target_dir, zoom=1, cpu_cores=1, gpu_nvidia_encoders=0, gpu_amd_encoders=0):
    video_extensions = ['webm', 'mp4', 'mkv']
    original_videos = [f for f in os.listdir(target_dir) if os.path.splitext(
        f)[-1][1:] in video_extensions and not f.startswith('converted_')]
    existing_converted = [f for f in os.listdir(target_dir) if os.path.splitext(
        f)[-1][1:] in video_extensions and f.startswith('converted_')]
    to_convert = [
        video for video in original_videos if f'converted_{os.path.splitext(video)[0]}.mp4' not in existing_converted]
    def output_maker(video, duration):
        return os.path.join(target_dir, 'converted_' + ('uncropped_' if duration <= 0 else '') + os.path.splitext(video)[0] + '.mp4')
    def convert(q, encoder):
        while q:
            video = q.popleft()
            cmd = ['ffmpeg', '-hwaccel', 'd3d11va', '-y','-i', os.path.join(target_dir, video)]
            duration = get_handled_media_duration(
                os.path.join(target_dir, video))
            if duration <= 0:
                duration = get_handled_media_duration(
                    os.path.join(target_dir, video))
            if duration > 0:
                cmd.extend(['-ss', str(duration * 0.05), '-t',
                           str(duration - 2 * duration * 0.05)])
            output = output_maker(video, duration)
            video_filters = f"scale={int(1920*zoom)}:{int(1080*zoom)}{',crop=1920:1080' if zoom > 1 else ''}"
            cmd.extend(['-vf', video_filters, '-c:v', encoder, '-g', '20','-keyint_min', '20', '-r', '20', '-b:v', '4M', '-an', output])
            if encoder == 'h264_amf':
                cmd.extend(['-usage', 'transcoding', '-profile','main', '-quality', 'balanced', '-rc', 'cbr'])
            if encoder == 'h264_nvenc':
                cmd.extend(['-preset', 'slow', '-rc:v', 'constqp', '-cq:v', '21',
                            '-profile:v', 'main', '-b:v', '4M', '-maxrate:v', '4M',
                            '-minrate:v', '4M', '-bufsize:v', '8M'])
            subprocess.run(cmd)
    video_queue = collections.deque(to_convert)
    with concurrent.futures.ThreadPoolExecutor(max_workers=cpu_cores + gpu_nvidia_encoders + gpu_amd_encoders) as executor:
        for _ in range(cpu_cores):
            executor.submit(convert, video_queue, 'libx264')
        for _ in range(gpu_nvidia_encoders):
            executor.submit(convert, video_queue, 'h264_nvenc')
        for _ in range(gpu_amd_encoders):
            executor.submit(convert, video_queue, 'h264_amf')


def convert_webm_to_mp3(directory_path):
    def convert(q):
        while q:
            webm_path = q.popleft()
            mp3_path = os.path.splitext(webm_path)[0] + '.mp3'
            command = [
                'ffmpeg',
                '-i', webm_path,
                '-vn',
                '-acodec', 'libmp3lame',
                mp3_path
            ]
            subprocess.run(command)
    q = collections.deque()
    for root, _, files in os.walk(directory_path):
        for filename in files:
            if filename.endswith('.webm'):
                webm_path = os.path.join(root, filename)
                q.append(webm_path)
    with concurrent.futures.ThreadPoolExecutor() as executor:
        for _ in range(8):
            executor.submit(convert, q)

def extract_video_data(folder_name):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_path = os.path.join(script_dir, folder_name)
    for dirpath, _, filenames in os.walk(base_path):
        json_files = [fname for fname in filenames if fname.endswith('.json')]
        mp3_files = [fname for fname in filenames if fname.endswith('.mp3')]
        if json_files and mp3_files:
            json_file_path = os.path.join(dirpath, json_files[0])
            with open(json_file_path, 'r', encoding="utf8") as json_file:
                json_data = json.load(json_file)
                title = json_data.get('title', '').strip()
                categories = json_data.get('categories', [])
                tags = json_data.get('tags', [])
                # description = json_data.get('description', [])
                with open(os.path.join(dirpath, 'title_english.txt'), 'w', encoding="utf8") as title_file:
                    title_file.write(title)
                '''with open(os.path.join(dirpath, 'desc_english.txt'), 'w', encoding="utf8") as desc_file:
                    desc_file.write(description.split('.')[0] + '...')'''
                with open(os.path.join(dirpath, 'categories_english.txt'), 'w', encoding='utf8') as categories_file:
                    for category in categories:
                        categories_file.write(f"{category}\n")
                with open(os.path.join(dirpath, 'tags_english.txt'), 'w', encoding='utf8') as tags_file:
                    for tag in tags:
                        tags_file.write(f"{tag}\n")


def map_and_move_files_to_folders(folder_name):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_path = os.path.join(script_dir, folder_name)
    audio_files, info_files = {}, {}
    for dirpath, _, files in os.walk(base_path):
        for f in files:
            if f.endswith('.json'):
                info_files[f] = os.path.join(dirpath, f)
            elif f.endswith('.mp3'):
                audio_files[f] = os.path.join(dirpath, f)
    for audio_name, audio_path in audio_files.items():
        basename = os.path.splitext(audio_name)[0]
        json_name = basename + '.json'
        if json_name in info_files:
            new_folder_path = os.path.join(base_path, basename)
            os.makedirs(new_folder_path, exist_ok=True)
            shutil.move(audio_path, os.path.join(new_folder_path, audio_name))
            shutil.move(info_files[json_name], os.path.join(new_folder_path, json_name))
            print(f"Moved {audio_name} and {json_name} to {new_folder_path}")
    return len(info_files)  # returns the total number of .json files processed

def map_files_to_folders(folder_name):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    school_path = os.path.join(script_dir, folder_name)
    os.chdir(school_path)
    audio_files, info_files = {}, {}
    # Gather all .mp3 and .json files with their paths
    for dirpath, _, files in os.walk('.'):
        for f in files:
            if f.endswith('.json'):
                info_files[f] = os.path.join(dirpath, f)
            elif f.endswith('.mp3'):
                audio_files[f] = os.path.join(dirpath, f)
    results = {}
    # For each .mp3 file, calculate similarity scores with all .json files
    for audio_name in audio_files.keys():
        scores = {}
        for info_name in info_files.keys():
            similarity = calculate_similarity_lev(audio_name, info_name)
            if similarity > 0:
                scores[info_name] = similarity
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        if sorted_scores:
            results[audio_name] = sorted_scores[0]
    return results, audio_files, info_files

def move_files_based_on_user_input(results, audio_files, info_files):
    for audio_name, (best_match_json, _) in results.items():
        print(f"{audio_name}")
        print(f"{best_match_json}")
        print("y/n ?")
        print('\n\n\n\n\n\n\n')
        user_input = input().strip().lower()
        if user_input == 'y':
            audio_path = audio_files[audio_name]
            json_path = info_files[best_match_json]
            folder_path = os.path.join(os.path.dirname(audio_path), os.path.splitext(audio_name)[0])
            os.makedirs(folder_path, exist_ok=True)
            shutil.move(audio_path, os.path.join(folder_path, audio_name))
            shutil.move(json_path, os.path.join(folder_path, best_match_json))

def get_playlist_links(playlist_url):
    cmd = ['yt-dlp', '-j', '--flat-playlist', playlist_url]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE)
    data = proc.stdout.decode()
    video_links = [f"https://www.youtube.com/watch?v={json.loads(line)['id']}" for line in data.splitlines()]
    return video_links

def second_downloader(urls, playlists, audio_video_mode, folder_name, metadata_only=False):

    os.makedirs(folder_name, exist_ok=True)

    format_option = [
        'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
        'bestvideo[height<=1080]/best[height<=1080]',
        'bestaudio/best',
        'bestvideo[height<=1080],bestaudio/best'
    ][audio_video_mode]

    def download_video(video_url):
        cmd = ['yt-dlp', '-o', f"{folder_name}/%(id)s/%(title)s.%(ext)s", '--write-description', '--write-thumbnail','--write-info-json', '--yes-playlist', '--sponsorblock-remove', 'all', video_url]

        if metadata_only:
            # This flag skips the actual download of the video/audio
            cmd.append('--skip-download')

        if not metadata_only:
            cmd.extend(['-f', format_option])

        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error downloading {video_url}: {str(e)}")

    video_links = urls

    for playlist_url in playlists:
        for link in get_playlist_links(playlist_url):
            video_links.append(link)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        executor.map(download_video, video_links)

def third_downloader(urls, playlists, audio_video_mode, folder_name, metadata_only=False):

    os.makedirs(folder_name, exist_ok=True)

    format_option = [
        'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
        'bestvideo[height<=1080]/best[height<=1080]',
        'bestaudio/best',
        'bestvideo[height<=1080],bestaudio/best'
    ][audio_video_mode]

    def download_video(video_url):
        cmd = ['yt-dlp', '-o', f"{folder_name}/%(title)s.%(ext)s", video_url]
        if metadata_only:
            # This flag skips the actual download of the video/audio
            cmd.append('--skip-download')
        if not metadata_only:
            cmd.extend(['-f', format_option])
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error downloading {video_url}: {str(e)}")

    video_links = urls

    for playlist_url in playlists:
        for link in get_playlist_links(playlist_url):
            video_links.append(link)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        executor.map(download_video, video_links)



def gpt_prompt(content, prompt=DEFAULT_PROMPT, model=DEFAULT_MODEL, temperature=0.2, max_retries=3, openai_keys):
    for key in openai_keys:
        headers = {"Content-Type": "application/json","Authorization": "Bearer " + key}
        data = {"model": model, "messages": [
            {"role": "user", "content": prompt + content}], "temperature": temperature}
        retries = 0
        while retries < max_retries:
            try:
                response = requests.post(
                    GPT_URL, headers=headers, data=json.dumps(data))
                response.raise_for_status()
                response_json = response.json()
                answer = response_json['choices'][0]['message']['content']
                return answer
            except requests.exceptions.RequestException as e:
                print(f"Exception with key {key}:", e)
                print("Retrying...")
                retries += 1
                time.sleep(1)
    raise Exception(
        "Failed to get a response after rotating through all API keys.")

def extract_content_from_folder(folder_name):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_path = os.path.join(script_dir, folder_name)
    dic = {}
    for dirpath, _, filenames in os.walk(base_path):
        current_folder_name = os.path.basename(dirpath)
        dic[current_folder_name] = {}
        for fname in filenames:
            text_file_path = os.path.join(dirpath, fname)
            if fname == 'title.txt':
                with open(text_file_path, 'r', encoding='utf8') as f_in:
                    title = f_in.read().strip()
                    dic[current_folder_name]['title_french'] = title
    return dic

def process_and_write_results(folder_name):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    results = extract_content_from_folder(folder_name)
    base_path = os.path.join(script_dir, folder_name)
    for fn in results:
        subfolder_path = os.path.join(base_path, fn)
        if not os.path.exists(subfolder_path):
            continue
        f1 = os.path.join(subfolder_path, 'title_french_spellchecked.txt')
        if os.path.exists(f1):
            print(f"Files already exist for folder {fn}. Skipping...")
            continue
        if results[fn]:
            title = results[fn]['title_french']
            content = title.strip()
            spell_checked = gpt_prompt(content)
            french_title_spellchecked = spell_checked.strip().strip('"').strip("'")
            with open(f1, "w", encoding="utf8") as title_file_spell_checked:
                title_file_spell_checked.write(french_title_spellchecked)
                print(french_title_spellchecked)


def get_json_playlist_links(playlists):
    cmd = ['yt-dlp', '-j', '--flat-playlist', playlist_url]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE)
    data = proc.stdout.decode()
    video_links = [json.loads(line)['id'] for line in data.splitlines()]
    return video_links

def create_file_if_not_there(filenames):
    for filename in filenames:    
        if filename not in os.listdir():
            with open(filename, 'w', encoding='utf8') as f_out:
                f_out.write('')    
                    
def transcriber_api(playlists):
    create_file_if_not_there(['data.txt', 'long_videos.txt', 'private_videos.txt', 'error_videos.txt'])
    videos = []
    for playlist in playlists:
        videos += get_json_playlist_links(sys.argv[2])
    with open('data.txt', 'w', encoding='utf8') as f_out:
        for vid in videos:
            f_out.write(vid + '\n')
    dataset = set([])
    def read_data():
        with open('data.txt', 'r', encoding='utf8') as data_file:
            for line in data_file.readlines():
                if line.strip() + '.txt' not in os.listdir():
                    dataset.add(line.strip())
    def long_videos(x):
        with open('long_videos.txt', 'a', encoding='utf8') as long_videos:
            long_videos.write(x + '\n')
    def private_videos(x):
        with open('private_videos.txt', 'a', encoding='utf8') as private_videos:
            private_videos.write(x + '\n')
    read_data()
    nopeset = set([])
    def read_nope():
        with open('private_videos.txt', 'r', encoding='utf8') as data_file:
            for line in data_file.readlines():
                if line.strip() + '.txt' not in os.listdir():
                    nopeset.add(line.strip())
        with open('long_videos.txt', 'r', encoding='utf8') as data_file:
            for line in data_file.readlines():
                if line.strip() + '.txt' not in os.listdir():
                    nopeset.add(line.strip())
    read_nope()
    for nop in nopeset:
        if nop in dataset:
            dataset.remove(nop)
    data = list(dataset)
    nope = list(nopeset)
    def update_data():
        with open('data.txt', 'w', encoding='utf8') as data_file:
            for l in data:
                data_file.write(l + '\n')
    update_data()
    client = Client("https://sanchit-gandhi-whisper-jax.hf.space/")
    print(f'\n\nthere are {len(data)} files left to transcribe')
    link_codes = data
    while data:
        random.shuffle(data)
        l = data.pop()
        if l not in os.listdir() and l not in nope:
            try:
                result = client.predict(l, "transcribe", False, api_name="/predict_2")
                print('\n' + l + ' done' + '\n')
                with open(l + '.txt', 'w', encoding='utf8') as f_out:
                    f_out.write(str(result))
                update_data()
            except Exception as e:
                if 'Maximum YouTube length is' in str(e):
                    long_videos(l)
                if 'private' in str(e) or 'Private' in str(e):
                    private_videos(l)
                if 'queue' in str(e) or 'Queue' in str(e):
                    data.append(l)
                
                print(f"Error processing {l}: {e}")
                wait_time = random.uniform(5, 10)
                print(f"Waiting for {wait_time:.2f} seconds before retrying...")
                time.sleep(wait_time)  
        else:
            update_data()

def prevent_sleep(window_title):
    ahk = AHK()
    win = ahk.find_window(title=window_title) # Find the opened window
    win.activate()           # Give the window focus
    ahk.mouse_move(x=100, y=100, blocking=True)  # Blocks until mouse finishes moving (the default)
    ahk.mouse_move(x=150, y=150, speed=10, blocking=True) # Moves the mouse to x, y taking 'speed' seconds to move
    print(ahk.mouse_position)  #  (150, 150)
    def simulate_activity():
        time.sleep(3 + random.randint(1,10)/10)
        win.activate() 
        while True:
            for j in range(random.randint(50, 100)):
                letters = [chr(ord('a') + i) for i in range(26)]
                for i in range(1, random.randint(1, 10)):
                    keyboard.press_and_release(random.choice(letters))
                    time.sleep(random.randint(100, 500)/1000)
                keyboard.press_and_release('space')
                time.sleep(random.randint(700, 1200)/1000)
            keyboard.press_and_release('enter')
            time.sleep(random.randint(10, 40))
            win.activate() 
    simulate_activity()

def make_readable():
    def myfunction(number):
        x = num2words(number, lang='fr')
        return str(x)
    def replace_numbers_with_function(input_filename, output_filename):
        roman_to_number = {str(fromRoman(roman)): r'\b' + roman +'e' + r'\b' for roman in ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII', 'XIII', 'XIV', 'XV', 'XVI', 'XVII', 'XVIII', 'XIX', 'XX', 'XXI']}
        number_separated_regex = r'(?<=[^\d\s])(\d+)(?=[^\d\s])'
        number_ending_with_e_regex = r'\b(\d+)(e)\b'
        with open(input_filename, 'r', encoding='utf-8') as input_file, open(output_filename, 'w', encoding='utf-8') as output_file:
            for i, line in enumerate(input_file):
                numbers_in_line = re.findall(r'\b\d+\b', line)
                for number in numbers_in_line:
                    if number + 'e' in line:
                        transformed_number = myfunction(int(number)) + 'ième'
                        print(input_filename + '     ' + str(i) + '        ', end=":     ")
                        print((i, number + 'e', transformed_number))
                        line = line.replace(number + 'e', str(transformed_number))
                    else:
                        transformed_number = myfunction(int(number))
                        print(input_filename + '     ' + str(i) + '        ', end=":     ")
                        print((i, number, transformed_number))
                        line = line.replace(number, str(transformed_number))
                separated_numbers_in_line = re.findall(number_separated_regex, line)
                for number in separated_numbers_in_line:
                    transformed_number = myfunction(int(number))
                    print(input_filename + '     ' + str(i) + '        ', end=":     ")
                    print((i, number, transformed_number))
                    line = re.sub(r'(?<=[^\d\s])' + number + r'(?=[^\d\s])', " " + str(transformed_number) + " ", line)
                for roman, numeral in roman_to_number.items():
                    if re.search(numeral, line):
                        transformed_number = myfunction(int(roman)) + 'ième'
                        print(input_filename + '     ' + str(i) + '        ', end=":     ")
                        print((i, numeral, transformed_number))
                        line = re.sub(numeral, str(transformed_number), line)
                output_file.write(line)
    replace_numbers_with_function('newest_french_alphabetical.txt', 'latest1.txt')

def paragraph_splitter(titleRegex, sectionRegex, input_file, output_file, X, Y):
    def split_paragraphs(section, X, Y):
        paragraphs = section.split("\n")
        new_paragraphs = []
        for para in paragraphs:
            if len(para) < X and new_paragraphs:
                if len(new_paragraphs[-1]) + len(para) <= Y:
                    new_paragraphs[-1] += " " + para
                elif len(new_paragraphs) > 1 and len(new_paragraphs[-2]) + len(para) <= Y:
                    new_paragraphs[-2] += " " + para
                else:
                    new_paragraphs.append(para)
            elif len(para) > Y:
                mid_index = len(para)//2
                split_index = max(para.rfind('.', 0, mid_index), para.rfind(',', 0, mid_index))
                if split_index == -1:
                    split_index = min(para.find('.', mid_index), para.find(',', mid_index))
                if split_index != -1 and para[split_index-1] != '"' and para[split_index+1] != '"':
                    new_paragraphs.append(para[:split_index+1].strip())
                    new_paragraphs.append(para[split_index+2:].strip())
                else:
                    new_paragraphs.append(para)
            else:
                new_paragraphs.append(para)
        return ('\n' + '*'*20 + '\n').join(new_paragraphs)
    
    with open(input_file, 'r', encoding='utf8') as file:
        corpus = file.read()
    parts = re.split(titleRegex, corpus, flags=re.MULTILINE)
    with open(output_file, 'w', encoding='utf8') as file:
        for part in parts:
            sections = re.split(sectionRegex, part, flags=re.MULTILINE)
            for section in sections:
                section = section.strip()  
                if section:
                    section = split_paragraphs(section, X, Y)
                    file.write(section + '\n')
                file.write('-'*20 + '\n')  
            file.write('+'*20 + '\n')

def add_pauses_to_audio():
    for i in range(1, 123):
        command = 'ffmpeg -i output' + str(i) + '.mp3 -filter_complex "[0:a]adelay=60000|60000[a]" -map "[a]" new_output' + str(i) + '.mp3'
        subprocess.call(command, shell=True)

def concat_audio_files():
    files = sorted([f for f in os.listdir() if f.endswith('.mp3') and f!='a.mp3'], key=lambda x: (int(x.split('-')[0]), int(x.split('-')[1].split('.')[0])))
    arr = []
    for file_name in files:
        if not arr or (arr[-1] and arr[-1][-1].split('-')[0] != file_name.split('-')[0]):
            arr.append([])
        arr[-1].append(file_name)
    for index, subarr in enumerate(arr):
        fname = 'input' + str(index+1) + '.txt'
        with open(fname, 'w') as input_file:
            for file_name in subarr:
                input_file.write(f"file {file_name}\n")
    for i in range(1, 123):
        command = 'ffmpeg -f concat -i input' + str(i) + '.txt -c copy output' + str(i) + '.mp3'
        subprocess.call(command, shell=True)

def replace_numerals():
    def myfunction(number):
        x = num2words(number, lang='fr')
        return str(x)
    def replace_numbers_with_function(input_filename, output_filename):
        roman_to_number = {str(fromRoman(roman)): r'\b' + roman +'e' + r'\b' for roman in ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII', 'XIII', 'XIV', 'XV', 'XVI', 'XVII', 'XVIII', 'XIX', 'XX', 'XXI']}
        number_separated_regex = r'(?<=[^\d\s])(\d+)(?=[^\d\s])'
        number_ending_with_e_regex = r'\b(\d+)(e)\b'
        with open(input_filename, 'r', encoding='utf-8') as input_file, open(output_filename, 'w', encoding='utf-8') as output_file:
            for i, line in enumerate(input_file):
                numbers_in_line = re.findall(r'\b\d+\b', line)
                for number in numbers_in_line:
                    if number + 'e' in line:
                        transformed_number = myfunction(int(number)) + 'ième'
                        print(input_filename + '     ' + str(i) + '        ', end=":     ")
                        print((i, number + 'e', transformed_number))
                        line = line.replace(number + 'e', str(transformed_number))
                    else:
                        transformed_number = myfunction(int(number))
                        print(input_filename + '     ' + str(i) + '        ', end=":     ")
                        print((i, number, transformed_number))
                        line = line.replace(number, str(transformed_number))
                separated_numbers_in_line = re.findall(number_separated_regex, line)
                for number in separated_numbers_in_line:
                    transformed_number = myfunction(int(number))
                    print(input_filename + '     ' + str(i) + '        ', end=":     ")
                    print((i, number, transformed_number))
                    line = re.sub(r'(?<=[^\d\s])' + number + r'(?=[^\d\s])', " " + str(transformed_number) + " ", line)
                for roman, numeral in roman_to_number.items():
                    if re.search(numeral, line):
                        transformed_number = myfunction(int(roman)) + 'ième'
                        print(input_filename + '     ' + str(i) + '        ', end=":     ")
                        print((i, numeral, transformed_number))
                        line = re.sub(numeral, str(transformed_number), line)
                output_file.write(line)
    replace_numbers_with_function('newest_french_alphabetical.txt', 'latest1.txt')

def split_into_paragraphs():
    def split_paragraphs(input_filename, output_filename):
        with open(input_filename, 'r', encoding='utf8') as file:
            data = file.read()
        sections = data.split('-------')
        with open(output_filename, 'w', encoding='utf8') as output_file:w
            for i, section in enumerate(sections):
                if section.strip() == '':
                    continue
                title, paragraph = section.split('*******')
                output_file.write('-------\n')
                output_file.write(title.strip() + '\n')
                if '.' not in paragraph:
                    print(f"No full stops found in paragraph at index {i}")
                    output_file.write('*******\n')
                    output_file.write(paragraph.strip() + '\n')
                    continue
                while len(paragraph) > 2000:
                    split_index = paragraph[:2000].rfind('.')
                    if split_index == -1:
                        # This would mean that there are more than 2000 characters without a full stop.
                        # Handle this case as you see fit. This script will just cut at the 2000th character.
                        split_index = 2000
                    small_paragraph = paragraph[:split_index+1].strip()
                    output_file.write('*******\n')
                    output_file.write(small_paragraph + '\n')
                    paragraph = paragraph[split_index+1:].strip()
                if paragraph != '':
                    output_file.write('*******\n')
                    output_file.write(paragraph + '\n')
    # Call the function
    split_paragraphs('corpus_french.txt', 'output_text.txt')

def elevenlabs_prompt(text_file, voice_code):
    headers = { "Accept": "audio/mpeg", "Content-Type": "application/json", "xi-api-key": ELEVEN_LABS_KEY}
    url = 'https://api.elevenlabs.io/v1/text-to-speech/' + voice_code

    def make_request(i, j, paragraph):
        payload = {
            'text': paragraph,
            "model_id": "eleven_multilingual_v1",
            'voice_settings': {
                'stability': 1,
                'similarity_boost': 0.2,
            }
        }
        while True:
            try:
                response = requests.post(url, headers=headers, json=payload)
                if response.status_code == 200:
                    filename = str(i) + '_' + str(j) + '.mp3'
                    with open(filename, 'wb') as f_out:
                        f_out.write(response.content)
                        print('Audio file saved')
                    print(paragraph + "\n" + filename + "\n-------------------------\n")
                    return
            except Exception:
                print("exception, retrying")
                time.sleep(1)
                
    with open(text_file, "r", encoding='utf8') as f_in:
        parts = f_in.read().split("-------")
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            for i, part in enumerate(parts):
                if part.strip():
                    paragraphs = part.split('*******')
                    for j, paragraph in enumerate(paragraphs):
                        if str(i) + '_' + str(j) + '.mp3' in get_files('mp3'):
                            continue
                        if paragraph.strip():
                            executor.submit(make_request, i, j, paragraph)

def get_files(s):
    os.chdir(os.getcwd())
    return glob('*.' + s)

def convert_wav_to_mp3():
    audio_files = get_files('wav')
    for audiofile in audio_files:
        command = 'ffmpeg -i ' + audiofile + ' -codec:a libmp3lame -qscale:a 2 ' + audiofile.split('.')[0] + '.mp3'
        subprocess.call(command, shell=True)

def remove_sound_from_mp4():
    for videofile in get_files('mp4'):
        new_vid = videofile.split('.')[0] + '_out.mp4'
        remove_audio_command = f'mkvmerge.exe -o ' + videofile.split('.')[0] + '.mkv -A ' + videofile
        subprocess.call(remove_audio_command, shell=True)

def add_delay():
    files = get_files('mp3')
    for i in range(200):
        if str(i) + '_0.mp3' in files :
            for j in range(200):
                if str(i) + '_' + str(j) + '.mp3' in files:
                    add_delay_command = 'ffmpeg -y -i ' + str(i) + '_' + str(j) + '.mp3 -filter_complex "[0:a]adelay=500|500[a]" -map "[a]" ' + str(i) + '_' + str(j) + '_out.mp3'
                    subprocess.call(add_delay_command, shell=True)
                    remove_old_file = 'rm ' + str(i) + '_' + str(j) + '.mp3'
                    subprocess.call(remove_old_file, shell=True)

def combine_audio_chunks():
    files = get_files('mp3')
    for i in range(200):
        if str(i) + '_0_out.mp3' in files :
            with open('input_file_' + str(i) + '.txt', 'w', encoding='utf8') as f_out:
                for j in range(200):
                    if str(i) + '_' + str(j) + '_out.mp3' in files:
                        f_out.write('file ' + str(i) + '_' + str(j) + '_out.mp3\n')
            command = 'ffmpeg -f concat -i input_file_' + str(i) + '.txt -c copy output_' + str(i) + '.mp3'
            subprocess.call(command, shell=True)

def renamer():
    # The directory with the .mp3 files and filenames.txt
    directory = os.path.abspath(os.getcwd())
    # Read the new filenames from the file
    with open(os.path.join(directory, 'filenames.txt'), 'r') as f:
        lines = f.read().splitlines()
    # Prepare a translator to remove punctuation
    translator = str.maketrans('', '', string.punctuation)
    for i, line in enumerate(lines, start=1):
        # Remove punctuation and replace spaces with underscores
        new_name = line.translate(translator).replace(' ', '_')
        # Form the old and new file paths
        old_file = os.path.join(directory, f'{i}.mp3')
        new_file = os.path.join(directory, f'{new_name}.mp3')
        # Check if file already exists, if so append a number
        if os.path.exists(new_file):
            duplicate_count = 1
            while os.path.exists(new_file):
                new_name += f"_{str(duplicate_count)}"
                new_file = os.path.join(directory, f'{new_name}.mp3')
                duplicate_count += 1
        # Rename the file
        if os.path.exists(old_file):
            os.rename(old_file, new_file)

def audio_file_cutter():
    CHUNK_LENGTH = 5 * 60 # Chunk length in seconds
    OVERLAP = 30 # Overlap in seconds
    BACKUP_FOLDER = "backup"
    MAX_WORKERS = 16 # Maximum number of concurrent threads
    # Create a backup folder if it doesn't exist
    if not os.path.exists(BACKUP_FOLDER):
        os.mkdir(BACKUP_FOLDER)
    # Get all mp3 files in the current directory
    mp3_files = [f for f in os.listdir(os.curdir) if f.endswith('.mp3')]
    def process_file(mp3_file):
        # Prepare a sanitized base file name
        base_name = os.path.splitext(mp3_file)[0]
        sanitized_name = re.sub(r'\W+', '_', base_name) # Replace non-alphanumeric characters with underscores
        # Get the duration of the file in seconds
        duration_command = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 \"{mp3_file}\""
        duration_output = subprocess.check_output(duration_command, shell=True)
        duration = int(float(duration_output.strip()))
        # Loop through the duration of the file with step size equal to chunk length - overlap
        for i in range(0, duration, CHUNK_LENGTH - OVERLAP):
            # Prepare the chunk file name
            chunk_file_name = f"{sanitized_name}_chunk_{int(i / (CHUNK_LENGTH - OVERLAP) + 1)}.mp3"
            # Cut the chunk out of the file
            chunk_command = f"ffmpeg -y -ss {i} -t {CHUNK_LENGTH} -i \"{mp3_file}\" \"{chunk_file_name}\""
            subprocess.call(chunk_command, shell=True)
        # Move the original file to the backup folder
        shutil.move(mp3_file, os.path.join(BACKUP_FOLDER, mp3_file))
    # Use ThreadPoolExecutor to run the process_file function in multiple threads
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        executor.map(process_file, mp3_files)

def text_joiner():
    files = get_files('txt')
    file_set = set(files)
    fset = set()
    for file in files:
        fset.add(file.split('_chunk_')[0])
    with open('output_final.txt', 'w', encoding='utf8') as f_out:
        for file in fset:
            f_out.write(file)
            for i in range(1, 100):
                if file + '_chunk_' + str(i) + '.txt' not in file_set:
                    break
                with open(file + '_chunk_' + str(i) + '.txt', 'r', encoding='utf8') as f_in:
                    f_out.write('\n*******\n')
                    f_out.write(f_in.read())
            f_out.write('\n-------\n')
    
def boundary_maker():
    with open('text1.txt', 'r', encoding='utf8') as f_in, open('text2.txt', 'w', encoding='utf8') as f_out:
        arr = f_in.read().split('-------')
        for part in arr:
            tab = part.split('*******')
            for paragraph in tab:
                start, end = paragraph, paragraph
                if len(paragraph) > 1000:
                    start, end = paragraph[:1000], paragraph[len(paragraph) - 1000:]
                f_out.write(start)
                f_out.write('\n\n.......\n\n')
                f_out.write(end)
                f_out.write('\n\n*******\n\n')
            f_out.write('\n\n-------\n\n')

def corpus_maker():
    def remove_text_inside_brackets(input_string):
        return re.sub(r'\[.*?\]', '', input_string)
    files = get_files('txt')
    with open('corpus_text.txt', 'w', encoding='utf8') as f_out:
        for file in files:
            new_name = remove_text_inside_brackets(file)
            new_name = new_name.replace('"', '')
            new_name = new_name.replace("'", "")
            new_name = new_name.replace(";", ",")
            new_name = new_name.replace(".txt", "")
            with open(file, 'r', encoding='utf8') as f_in:
                text = f_in.read()
                f_out.write(new_name)
                f_out.write('\n*******\n')
                f_out.write(text)
                f_out.write('\n-------\n')

def numeral_remover_2():
    def myfunction(number):
        x = num2words(number, lang='fr')
        return str(x)

    def replace_numbers(text):
        def convert_number(match):
            number = int(match.group())
            return ' ' + num2words(number, lang='fr') + ' '
        return re.sub(r'\d+', convert_number, text)

    def replace_numbers_with_function(input_filename, output_filename):
        with open(input_filename, 'r', encoding='utf-8') as input_file, open(output_filename, 'w', encoding='utf-8') as output_file:
            arr = input_file.read().split('-------')
            for string in arr:
                output_file.write(string.split('*******')[0] + '\n')
                output_file.write('*******\n')
                replaced = replace_numbers('*******'.join(string.split('*******')[1:]))
                output_file.write(replaced+'\n')
                output_file.write('-------\n')
            
    replace_numbers_with_function('denum_corpus_french.txt', 'denum_corpus_french_1.txt')

def get_article_info(article_url):
    response = requests.get(article_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    article_title = soup.find('h1', class_='story-title').text.strip()
    
    try:
        article_date = soup.find('div', class_='story-head').find('p').text.strip()
    except:
        article_date = "No date provided"

    paragraphs = []
    container = soup.find('div', class_='paragraphs-container')
    for elem in container:
        if isinstance(elem, NavigableString):
            continue
        if elem.name.lower() == 'h3' and elem.text.strip().lower() == 'transcript':
            break
        if elem.name.lower() == 'p':
            paragraphs.append(elem.text)

    article_text = '\n'.join(paragraphs)

    return article_title, article_date, article_text

def extract_info():
    url = 'https://text.npr.org/' #Replace with your actual website's URL
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    articles = soup.find('div', class_='topic-container').find_all('li')
    
    output_file = open('output.txt', 'w', encoding='utf8')

    for article in articles:
        link = article.find('a')['href']
        article_url = url + link #Assuming relative links in href, otherwise use directly
        
        title, date, text = get_article_info(article_url)

        output_file.write('Title: {}\n'.format(title))
        output_file.write('Date: {}\n'.format(date))
        output_file.write('Article Text:\n{}\n'.format(text))
        output_file.write('--------\n')

    output_file.close()

def keyword_maker():
    with open('output.txt', "r", encoding='utf8') as f_in:
        arr = f_in.read().split("--------")
        with open('keywords.txt', "w", encoding='utf8') as f_out:
            f_out.write("----------")
            for part in arr:
                if len(part) == 0 or 'Article Text:' not in part:
                    continue
                title = part.split('Article Text:')[0].split('Date')[0]
                paragraph = part.split('Article Text:')[1]
                data = {
                    "model": "gpt-3.5-turbo", 
                    "messages": [
                        {
                            "role": "user", 
                            "content": "write both a compeling title and a comma separated in line list of youtube keyword for this news article, the list should not be above 500 characters in total (the commas don't count): \n Title: " + title + " \n Article: \n" + paragraph,
                        }
                    ]
                }
                retry=True
                k = 0
                while retry:
                    try:
                        response = requests.post(url, headers=headers, data=json.dumps(data))
                        response_json = response.json()
                        answer = response_json['choices'][0]['message']['content']
                        print(answer)
                        print("\n")
                        f_out.write("\n")
                        f_out.write(answer)
                        f_out.write("\n")
                        f_out.write("----------")
                        time.sleep(1)
                        k = 0
                        retry = False
                    except Exception:
                        print("exception, retrying")
                        k += 1
                        if k >= 3:
                            k = 0
                            retry = False
                        time.sleep(1)

def main():
    # The first element in sys.argv is the name of the script itself
    script_name = sys.argv[0]
    
    # The rest of the elements are the command-line arguments
    arguments = sys.argv[1:]
        
    if arguments:
        
        print("Arguments:")

        if len(arguments) == 1 and arguments[0] == "-h":
            print(HELP_INFO)
            
        elif len(arguments) == 3 and arguments[0] == "--randomized_music":
            source_dir, output_dir = arguments[1], arguments[2]
            parallel_batch_tast(8, source_dir, output_dir, True, create_randomized_music_file)
        elif len(arguments) == 3 and arguments[0] == "--merge_music_voice":
            source_dir, output_dir = arguments[1], arguments[2]
            parallel_batch_tast(8, source_dir, output_dir, True, merge_music_with_voice)
        elif len(arguments) == 3 and arguments[0] == "--split_video_in_chunks":
            source_dir, output_dir = arguments[1], arguments[2]
            parallel_batch_tast(8, source_dir, output_dir, True, split_video_into_chunks)
        elif len(arguments) == 3 and arguments[0] == "--merge_music_voice":
            source_dir, output_dir = arguments[1], arguments[2]
            parallel_batch_tast(8, source_dir, output_dir, True, add_fade_in_fade_out)
        elif len(arguments) == 3 and arguments[0] == "--combine_videos":
            source_dir, output_dir = arguments[1], arguments[2]
            combine_videos(source_dir, output_dir)
        elif len(arguments) == 4 and arguments[0] == "--upload_youtube":
            folder_name, google_client, google_secret = arguments[1], arguments[2], arguments[3]
            process_directory(folder_name, google_client, google_secret, auth=True)
        elif len(arguments) == 2 and arguments[0] == "--random_rename": 
            target_dir = arguments[1]
            general_rename(target_dir, random_rename, True, replaced="", number_if_found=False)
        elif len(arguments) == 4 and arguments[0] == "--thumbnail_maker":
            content_folder, bg_folder, layer_folder = arguments[1], arguments[2], arguments[3]
            process_images(content_folder, bg_folder, layer_folder)
        elif len(arguments) == 6 and arguments[0] == "--trim_and_convert":
            target_dir, zoom, cpu_cores, gpu_nvidia_encoders, gpu_amd_encoders = arguments[1], arguments[2], arguments[3], arguments[4], arguments[5]
            process_videos(target_dir, zoom, cpu_cores, gpu_nvidia_encoders, gpu_amd_encoders):
        elif len(arguments) == 2 and arguments[0] == "--convert_webm_mp3":
            convert_webm_to_mp3(arguments[1])
        elif len(arguments) == 2 and arguments[0] == "--extract_video_data":
            extract_video_data(arguments[1])
        elif len(arguments) == 2 and arguments[0] == "--map_and_move":
            map_and_move_files_to_folders(arguments[1])
        elif len(arguments) == 2 and arguments[0] == "--similarity_map_and_move":
            map_files_to_folders(arguments[1])
        elif len(arguments) == 4 and arguments[0] == "--user_similarity_map_and_move":
            move_files_based_on_user_input(arguments[1], arguments[2], arguments[3])
        elif len(arguments) == 6 and arguments[0] == "--structured_download":
            urls = arguments[1].split(',')
            playlists = arguments[2].split(',')
            audio_video_mode = int(arguments[3])
            folder_name = arguments[4]
            metadata_only = int(arguments[5]) != 0 
            second_downloader(urls, playlists, audio_video_mode, folder_name, metadata_only)
        elif len(arguments) == 6 and arguments[0] == "--resource_download":
            urls = arguments[1].split(',')
            playlists = arguments[2].split(',')
            audio_video_mode = int(arguments[3])
            folder_name = arguments[4]
            metadata_only = int(arguments[5]) != 0 
            third_downloader(urls, playlists, audio_video_mode, folder_name, metadata_only)
        elif len(arguments) == 7 and arguments[0] == "--gpt_prompter":
            content = argumeents[1]
            prompt = arguments[2] 
            model = arguments[3]
            temperature = arguments[4]
            max_retries = arguments[5]
            openai_keys = arguments[6].split(',')
            gpt_prompt(content, prompt, model, temperature, max_retries, openai_keys)
        elif len(arguments) == 2 and arguments[0] == "--transcriber_api":
            transcriber_api(arguments[1].split(','))
        else:
            print("No arguments provided.")

"""
        paragraph_splitter(titleRegex, sectionRegex, input_file, output_file, X, Y)
        add_pauses_to_audio()
        concat_audio_files()
        replace_numerals()
        elevenlabs_prompt(text_file, voice_code)
        add_delay()
        combine_audio_chunks()
        keyword_maker()
"""   

if __name__ == "__main__":
    main()
