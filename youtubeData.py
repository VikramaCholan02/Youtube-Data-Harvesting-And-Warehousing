from googleapiclient.discovery import build
import mysql.connector
import pandas as pd
from datetime import datetime
import re
import streamlit as st
from dateutil import parser

Api_Id = "AIzaSyDDPYLyYvkyS7akIiKyoYSygDAzGcWvd6o"

CHANNEL_ID =""

def Api_connect():
    Api_ID="AIzaSyDDPYLyYvkyS7akIiKyoYSygDAzGcWvd6o"

    api_service_name = "youtube"
    api_version = "v3"

    youtube =build(api_service_name, api_version, developerKey=Api_Id)

    return youtube

youtube = Api_connect()


def get_channel_details(c_id):
    response = youtube.channels().list(
                  part="snippet,contentDetails,statistics",
                  id=c_id).execute()
    
    channel_data = []
    for item in response.get("items", []):
               
        published_at = parser.parse(response['items'][0]["snippet"]["publishedAt"]).strftime("%Y-%m-%d %H:%M:%S")
        data=dict(channel_name =response['items'][0]["snippet"]["title"],
                    channel_Id =response['items'][0]["id"],
                    publishe_at =published_at,
                    playlist_id =response['items'][0]["contentDetails"]["relatedPlaylists"]["uploads"],
                    sub_count =response['items'][0]["statistics"]["subscriberCount"],
                    view_Count =response['items'][0]["statistics"]["viewCount"],
                    video_count =response['items'][0]["statistics"]["videoCount"],
                    channel_description =response['items'][0]["snippet"]["description"])
        channel_data.append(data)
    return channel_data
    
def get_videos_ids(c_id):
    video_ids=[]
    request = youtube.channels().list( id=c_id,part='contentDetails')
    response = request.execute()
    playlist_id =response['items'][0]['contentDetails']['relatedPlaylists']['uploads']

    next_page_token = None
    while True:
        response1 = youtube.playlistItems().list(part = 'snippet',
                                                playlistId =playlist_id,
                                                maxResults=50,
                                                pageToken=next_page_token).execute() 
                                                
        for i in range(len(response1['items'])):
            video_ids.append(response1['items'][i]['snippet']['resourceId']['videoId'])
        next_page_token =  response1.get('nextPageToken')
        
        if next_page_token is None:
            break
    return video_ids

#convertion of vid_durarion into min and sec.
def duration_to_sec(Vid_Duration):
    match = re.match(r"^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$", Vid_Duration)
    if not match:
        return 0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    if hours == 0:
        return (f'{minutes}mins : {seconds}sec')
    else:
        return (f'{hours}hrs : {minutes}mins:{seconds}sec')

def get_video_info(video_ids):
    video_data = []
    for video_id in video_ids:
        request = youtube.videos().list( part = "snippet,ContentDetails,statistics", id = video_id)

        response = request.execute()

        for item in response["items"]:
            Vid_Duration = item['contentDetails']['duration']
            converted_duration = duration_to_sec(Vid_Duration)   # Corrected from ['Vid_Duration']
            published_date = item['snippet']['publishedAt']
            published_date = datetime.strptime(published_date, '%Y-%m-%dT%H:%M:%SZ').strftime('%Y-%m-%d %H:%M:%S')

            data2 = dict(Channel_Name=item['snippet']['channelTitle'],
                        Channel_Id= item['snippet']['channelId'],
                        Video_Id=item['id'],
                        Vid_Title=item['snippet']['title'],
                        Tags=item['snippet'].get('tags')[0] if item['snippet'].get('tags') else None,
                        Vid_Thumbnail=item['snippet']['thumbnails']['default']['url'],
                        Vid_Description=item['snippet'].get('description'),
                        Vid_Published_Date=published_date,
                        Vid_Duration=converted_duration,
                        Views=item['statistics'].get('viewCount'),
                        likes=item['statistics'].get('likeCount'),
                        Comments=item['statistics'].get('commentCount'),
                        Favourite_count=item['statistics']['favoriteCount'],
                        Definition=item['contentDetails']['definition'],
                        Caption_Status=item['contentDetails']['caption']
                        )
            video_data.append(data2)
    return video_data   

# get comment information
def get_comment_info(video_ids):
    Comment_data=[]
    try:
        for video_id in video_ids:
            request = youtube.commentThreads().list( part="snippet", videoId=video_id, maxResults=100)
               
            response = request.execute()

            for item in response['items']:
                Comment_Published = datetime.strptime(item['snippet']['topLevelComment']['snippet'].get('publishedAt'), "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d %H:%M:%S")
                data3=dict(Comment_Id=item['snippet']['topLevelComment']['id'],
                        Video_Id=item['snippet']['topLevelComment']['snippet']['videoId'],
                        Comment_Text=item['snippet']['topLevelComment']['snippet']['textDisplay'],
                        Comment_Author=item['snippet']['topLevelComment']['snippet']['authorDisplayName'],
                        Comment_Published=Comment_Published)
                
                Comment_data.append(data3)
    except:
        pass
    return Comment_data   

# CHANNEL TABLE CREATION AND DETAILS INSERTING INTO MYSQL

def channels_table():
    mydb=mysql.connector.connect(host="localhost",
                                user="root",
                                password="rootroot",
                                database="youtube_data_harvesting",
                                port="3306")
    cursor = mydb.cursor()


    try:
        create_query='''create table if not exists channels(channel_name varchar(100),
                                                            channel_Id varchar(100) primary key,
                                                            publishe_at varchar(100),
                                                            sub_count bigint,
                                                            view_Count bigint,
                                                            video_count int,
                                                            channel_description text,
                                                            playlist_id varchar(100))'''
        cursor.execute(create_query)
        mydb.commit()
    except:
        print("channels table already created")

    # Fetch channel details
    channel_details = get_channel_details(CHANNEL_ID)

    # Convert the list of dictionaries to a DataFrame
    df1 = pd.DataFrame(channel_details)

    for index,row in df1.iterrows():
            insert_query='''insert into channels(channel_name,
                                                channel_Id,
                                                publishe_at,
                                                sub_count,
                                                view_Count,
                                                video_count,
                                                channel_description,
                                                playlist_id)
                                                
                                            values(%s,%s,%s,%s,%s,%s,%s,%s)'''
    values=(row['channel_name'],row['channel_Id'],row['publishe_at'],row['sub_count'],row['view_Count'],
            row['video_count'],row['channel_description'],row['playlist_id'])
        
    try:
            cursor.execute(insert_query,values)
            mydb.commit()
    except:
            print("channels values are already inserted")

# VIDEOS TABLE CREATION AND DETAILS INSERTING INTO MYSQL

def videos_table():
    mydb=mysql.connector.connect(host="localhost",
                                user="root",
                                password="rootroot",
                                database="youtube_data_harvesting",
                                port="3306")
    cursor = mydb.cursor()


    create_query='''create table if not exists videos(Channel_Name varchar(100),
                                                    channel_Id varchar(100),
                                                    Video_Id varchar(100) primary key,
                                                    Vid_Title varchar(150),
                                                    Tags text,
                                                    Vid_Thumbnail varchar(200),
                                                    Vid_Description text,
                                                    Vid_Published_Date datetime,
                                                    Vid_Duration varchar(250),
                                                    Views bigint,
                                                    likes bigint,
                                                    Comments int,
                                                    Favourite_count int,
                                                    Definition varchar(10),
                                                    Caption_Status varchar(50))'''
    cursor.execute(create_query)
    mydb.commit()

    # Fetch video details
    #vi_2
    video_ids = get_videos_ids(CHANNEL_ID)
    video_details = get_video_info(video_ids)
    df2 = pd.DataFrame(video_details)

    #inserting of video details and channel table.
    # vi_3


    for index,row in df2.iterrows():
    
            insert_query='''insert into videos(Channel_Name,
                                            Channel_Id,
                                            Video_Id,
                                            Vid_Title,
                                            Tags,
                                            Vid_Thumbnail,
                                            Vid_Description,
                                            Vid_Published_Date,
                                            Vid_Duration,
                                            Views,
                                            likes,
                                            Comments,
                                            Favourite_count,
                                            Definition,
                                            Caption_Status)
                                            
                                            values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)'''
            values=(row['Channel_Name'],row['Channel_Id'],row['Video_Id'],row['Vid_Title'],row['Tags'],
            row['Vid_Thumbnail'],row['Vid_Description'],row['Vid_Published_Date'],row['Vid_Duration'],row['Views'],
            row['likes'],row['Comments'],row['Favourite_count'],row['Definition'],row['Caption_Status'])
            
            try:
                cursor.execute(insert_query,values)
                mydb.commit()
            except:
               print("videos values are already inserted")

# COMMENT TABLE CREATION AND DETAILS INSERTING INTO MYSQL

def comments_table():
    mydb = mysql.connector.connect(host="localhost",
                                user="root",
                                password="rootroot",
                                database="youtube_data_harvesting",
                                port="3306",
                                charset="utf8mb4")
    cursor = mydb.cursor()

    create_query = '''create table if not exists comments(Comment_Id varchar(100) primary key,
                                                        Video_Id varchar(50),
                                                        Comment_Text text,
                                                        Comment_Author varchar(200),
                                                        Comment_Published timestamp)'''
    cursor.execute(create_query)
    mydb.commit()

    # comment details and data frame conversion.
    video_ids = get_videos_ids(CHANNEL_ID)
    comment_details=get_comment_info(video_ids) 
    for i in range(len(["comment_details"])):
        # data_frame
        df3 = pd.DataFrame(comment_details)


    # insert query for comment details in mysql
    for index, row in df3.iterrows():
        
        insert_query = '''insert into comments(Comment_Id,
                                                Video_Id,
                                                Comment_Text,
                                                Comment_Author,
                                                Comment_Published)
                                                
                                            values(%s,%s,%s,%s,%s)'''
        values = (row['Comment_Id'], row['Video_Id'], row['Comment_Text'], row['Comment_Author'],row['Comment_Published'])

        try:
            cursor.execute(insert_query, values)
            mydb.commit()
        except:
            print("comments values are already inserted")


def tables(channel_id):
    # Set the global CHANNEL_ID variable to the provided channel_id
    global CHANNEL_ID
    CHANNEL_ID = channel_id
    channels_table()
    videos_table()
    comments_table()

    return "tables created successfully"

#Tables = tables()

def show_channels_table(channel_id):
    # Fetch channel details
    channel_details = get_channel_details(channel_id)

    # Convert the list of dictionaries to a DataFrame
    df1 = st.dataframe(channel_details)

    return df1

def show_videos_table(channel_id):   
    # Fetch video details
    #vi_2
    video_ids = get_videos_ids(channel_id)
    video_details = get_video_info(video_ids)
    df2 = st.dataframe(video_details)
 
    return df2

def show_comments_table(channel_id):
    # comment details and data frame conversion.
    video_ids = get_videos_ids(channel_id)
    comment_details=get_comment_info(video_ids) 
    for i in range(len(["comment_details"])):
        # data_frame
        df3 = st.dataframe(comment_details)

        return df3

# STREAMLIT CREATING

def show_home():
    st.title(":red[YOUTUBE DATA HARVESTING AND WAREHOUSING]")
    st.write("""
    Overview:
        The YouTube Data Harvesting and Warehousing project aims to collect, store, and analyze data from YouTube using Python 
        programming, web scraping techniques, MySQL for data warehousing, and Streamlit for data presentation. By leveraging these 
        technologies, the project facilitates the extraction of valuable insights from YouTube's vast repository of videos, comments, and metadata.
             
    ## KEY COMPONENTS:

    1.PYTHON PROGRAMMING:
        Python will serve as the primary programming language for this project. It will be used for various tasks such as web
         scraping, data manipulation, analysis, and integration with MySQL database.
    2.WEB SCRAPING:
        Utilizing libraries like BeautifulSoup and Scrapy, web scraping techniques will be employed to extract data
        from YouTube. This includes retrieving information about videos, comments, likes, dislikes, view counts, and other relevant metadata.
    3.MySQL DATABASE:
        MySQL will be used as the backend database management system for storing the harvested YouTube data.
         The schema will be designed to efficiently organize the collected information for easy retrieval and analysis.
    4.DATA WAREHOUSING:
        The collected YouTube data will be stored in the MySQL database, following best practices for data
        warehousing. This involves designing a schema optimized for querying and reporting, as well as implementing data cleaning and transformation processes to ensure data quality.
    5.STREAMLIT:
        Streamlit, a Python library for creating interactive web applications, will be used to develop a user-friendly
        interface for presenting the harvested YouTube data. Through Streamlit, users will be able to visualize insights, perform queries, and explore the dataset in an intuitive manner.
             
    ## PROJECT WORKFLOW:

    1.DATA COLLECTION:
        Use web scraping techniques to gather data from YouTube, including video details, comments, and related metadata.
        Implement robust error handling and rate limiting to ensure data retrieval complies with YouTube's terms of service.
    2.DATA STROAGE:
        Design a MySQL database schema to store the harvested YouTube data.
        Establish connections to the MySQL database and develop functions for inserting, updating, and querying data.
    3.DATA WAREHOUSING:
        Clean and preprocess the collected data to ensure consistency and reliability.
        Apply data transformation techniques to optimize the dataset for analysis and reporting.
    4.USER INTERFACE DEVELOPMENT:
        Utilize Streamlit to create a web-based interface for accessing and interacting with the YouTube data.
        Design intuitive visualizations and controls to facilitate data exploration and analysis.
    5.DEVELOPMENT AND TESTING:
        Deploy the application on a suitable web server or cloud platform.
        Conduct comprehensive testing to ensure the functionality, performance, and security of the application.
    """)


def show_project():
    channel_id = st.text_input("Enter the channel ID")

    if st.button("Collect Data"):
        # Fetch channel details
        channel_details = get_channel_details(channel_id)
        video_ids = get_videos_ids(channel_id)  
        video_details = get_video_info(video_ids)
        comment_details=get_comment_info(video_ids) 
        st.success("Channel data collected successfully!")


    # Migrate to SQL if requested
    if st.button("Migrate to SQL"):
        Tables=tables(channel_id)
        st.success(Tables)

    show_table = st.radio("SELECT THE TABLE FOR VIEW", ("CHANNELS", "VIDEOS", "COMMENTS"))

    if show_table == "CHANNELS":
       show_channels_table(channel_id)
    elif show_table == "VIDEOS":
        show_videos_table(channel_id)

    elif show_table == "COMMENTS":
         show_comments_table(channel_id)
def show_queries():
    mydb = mysql.connector.connect(host="localhost",
                            user="root",
                            password="rootroot",
                            database="youtube_data_harvesting",
                            port="3306",
                            charset="utf8mb4")
    cursor = mydb.cursor()

    question=st.selectbox("SELECT YOUR QUESTION",("1. All the videos and the channel name",
                                                  "2. channels with most number of videos",
                                                  "3. 10 most viewed videos and their channels",
                                                  "4. No.of comments in each videos",
                                                  "5. Videos with higest likes and their channel",
                                                  "6. Total No.of likes of all videos",
                                                  "7. Total No.of views of each channel",
                                                  "8. Channels with videos published in the year of 2022",
                                                  "9. average duration of all videos in each channel",
                                                  "10. videos with highest number of comments"))
    
    if question=="1. All the videos and the channel name":
        query1='''select Vid_Title as videos,Channel_Name as channelname from videos'''
        cursor.execute(query1)
        #mydb.commit()
        t1=cursor.fetchall()
        df=pd.DataFrame(t1,columns=["video title","channel name"])
        st.write(df)

    elif question=="2. channels with most number of videos":
        query2='''select channel_name as channelname,video_count as no_videos from channels
                order by video_count  desc'''
        cursor.execute(query2)
        #mydb.commit()
        t2=cursor.fetchall()
        df2=pd.DataFrame(t2,columns=["channel name","No of videos"])
        st.write(df2)

    elif question=="3. 10 most viewed videos and their channels":
        query3='''select Views as views,Channel_Name as channelname,Vid_Title as videotitle from videos
                    where views is not null order by Views desc limit 10'''
        cursor.execute(query3)
        #mydb.commit()
        t3=cursor.fetchall()
        df3=pd.DataFrame(t3,columns=["views","channel name","videotitle"])
        st.write(df3)

    elif question=="4. No.of comments in each videos":
        query4='''select Comments as no_comments,Vid_Title as videotitle from videos where comments is not null'''
        cursor.execute(query4)
        #mydb.commit()
        t4=cursor.fetchall()
        df4=pd.DataFrame(t4,columns=["no of comments","videotitle"])
        st.write(df4)

    elif question=="5. Videos with higest likes and their channel":
        query5='''select Vid_Title as videotitle,Channel_Name as channalname,likes as likecount
                        from videos where likes is not null order by likes desc'''
        cursor.execute(query5)
        #mydb.commit()
        t5=cursor.fetchall()
        df5=pd.DataFrame(t5,columns=["videotitle","channelname","likecount"])
        st.write(df5)

    elif question=="6. Total No.of likes of all videos":
        query6='''select likes as likecount,Vid_Title as videotitle from videos'''
        cursor.execute(query6)
        #mydb.commit()
        t6=cursor.fetchall()
        df6=pd.DataFrame(t6,columns=["likecount","videotitle"])
        st.write(df6)

    elif question=="7. Total No.of views of each channel":
            query7='''select channel_name as channelname,view_Count as totalviews from channels'''
            cursor.execute(query7)
            #mydb.commit()
            t7=cursor.fetchall()
            df7=pd.DataFrame(t7,columns=["channel name","totalviews"])
            st.write(df7)

    elif question=="8. Channels with videos published in the year of 2022":
        query8='''select Vid_Title as video_title, Vid_Published_Date as videorelease,Channel_Name as channel_name from videos
                    where extract(year from Vid_Published_Date)=2022'''
        cursor.execute(query8)
        #mydb.commit()
        t8=cursor.fetchall()
        df8=pd.DataFrame(t8,columns=["videotitle","Published_date","channel name"])
        st.write(df8)

    elif question == "9. average duration of all videos in each channel":
        query9 = '''SELECT Channel_Name AS `channel name`, AVG(Vid_Duration) AS `averageduration` FROM videos GROUP BY Channel_Name'''
        cursor.execute(query9)
        # mydb.commit()
        t9 = cursor.fetchall()
        df9 = pd.DataFrame(t9, columns=["channel name", "averageduration"])
        
        T9 = []
        for index, row in df9.iterrows():
            channel_name = row["channel name"]
            average_duration = row["averageduration"]
            average_duration_str = str(average_duration)
            T9.append(dict(channeltitle=channel_name, avgduration=average_duration_str))
        df2 = pd.DataFrame(T9)
        st.write(df2)


    elif question=="10. videos with highest number of comments":
        query10='''select Vid_Title as videotitle,Channel_Name as channelname,Comments as comments from videos where 
                   comments is not null order by Comments desc'''
        cursor.execute(query10)
        #mydb.commit()
        t10=cursor.fetchall()
        df10=pd.DataFrame(t10,columns=["videotitle","channel name","comments"])
        st.write(df10)

# Sidebar
selected_page = st.sidebar.selectbox('Navigation',('Home', 'Project', 'Queries'))

if selected_page == 'Home':
    show_home()
elif selected_page == 'Project':
    show_project()
elif selected_page == 'Queries':
    show_queries()