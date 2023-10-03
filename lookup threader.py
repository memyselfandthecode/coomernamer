import bs4
import requests
import re
import os
import hashlib
import time
import threading
from tqdm import tqdm


# Put all file from directory into a list
def get_files(directory):
    files = []
    for file in os.listdir(directory):
        if (
            file.split(".")[-1] == "mp4"
            or file.split(".")[-1] == "mkv"
            or file.split(".")[-1] == "webm"
            or file.split(".")[-1] == "m4v"
        ) and " " not in file:
            if file.split(".")[-1] != "part":
                files.append(file.split("."))
    return files


# get sha256 hash of file
def get_hash(file_path):
    stopwatch = time.time()
    BLOCKSIZE = 10485760
    hasher = hashlib.sha256()
    with open(f"{file_path}", "rb") as afile:
        buf = afile.read(BLOCKSIZE)
        while len(buf) > 0:
            hasher.update(buf)
            buf = afile.read(BLOCKSIZE)
    # print(
    #    f"Hashed {file_path} in {time.time()-stopwatch} seconds on thread {threading.current_thread().name}"
    # )
    return [hasher.hexdigest(), file_path]


def hash_files(files, directory, num_threads=12):
    start_time = time.time()
    results = [None] * len(files)
    threads = []
    for i in range(num_threads):
        thread_files = files[i::num_threads]
        thread = threading.Thread(
            target=hash_files_thread,
            args=(thread_files, directory, results, i, num_threads),
        )
        threads.append(thread)
        thread.start()
        # print(f"Started thread {i} of {num_threads}")
    for thread in tqdm(threads, desc="Hashing files", position=0):
        thread.join()
    end_time = time.time()
    # print(f"Hashed {len(files)} files in {end_time - start_time:.2f} seconds")
    return results


# Define a function to hash files in a single thread
def hash_files_thread(files, directory, results, thread_index, num_threads):
    counter = 0
    for i, file in tqdm(
        enumerate(files), desc=f"Hashing thread {thread_index}", leave=True
    ):
        file_path = directory + "/" + file[0] + "." + file[1]
        results[thread_index + i * num_threads] = get_hash(file_path)
        # print(f"Hashed {counter} of {len(files)} files", end="\r")


# search for files in hash lookup online
def search_hash(hash, directory):
    url = f"https://coomer.party/search_hash?hash={hash}"
    response = requests.get(url)
    soup = bs4.BeautifulSoup(response.text, "html.parser")
    try:
        link = soup.find("article").find("a").get("href")
        performer = link.split("/")[3]
        print(f"Found {performer}")
    except:
        print(f"Could not find with hash: {hash}")
        return "Not Found", "Not Found"
    print("link", link, "from file", directory)

    url = f"https://coomer.party{link}"
    response = requests.get(url)
    soup = bs4.BeautifulSoup(response.text, "html.parser")
    try:
        title = soup.find("div", class_="post__content").find("pre").text
    except:
        return "Not Found", "Not Found"
    title = re.sub(r"[^\w\s]", "", title)
    title = title[:50]
    title = title.split("\n")[0]
    return title, performer


# rename the file making sure to keep the extension
def rename_file(title, directory, performer):
    ext = directory.split(".")[-1]
    filename = directory.split("/")[-1].split(".")[0]
    fro = directory
    t = f"{directory.rstrip('/'+filename+'.'+ext)}/{title} ({performer}).{ext}"
    os.rename(fro, t)
    print(f"Renamed {directory} to {title}.{directory.split('.')[-1]}")


# Main function
def main():
    directory = input("Enter directory: ")
    files = get_files(directory)
    hashes = hash_files(files, directory)
    tried = []
    renamed = []
    run = 0
    for file in hashes:
        # print(f"File {run} out of {len(hashes)}", end="\r")
        run += 1
        title, performer = search_hash(file[0], file[1])
        if title == "Not Found":
            tried.append(file)
            continue
        try:
            rename_file(title, file[1], performer)
            renamed.append(file)
        except:
            tried.append(file)

    print(f"Renamed {len(renamed)} files out of {len(files)}")


main()
