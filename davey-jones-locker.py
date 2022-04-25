
#Importing packages
#
import os
import pandas as pd
from github import Github

# To work with the .env file
from dotenv import load_dotenv
load_dotenv()


# Leave This code here and lookup at pandas documentation 
# if you need to know about chained assignments
pd.options.mode.chained_assignment = None  # default='warn'


# Get our block frost api key from the file .env
api_key = os.getenv('WAEL_BLOCKFROST_API_KEY')

from blockfrost import BlockFrostApi, ApiError, ApiUrls

api = BlockFrostApi(
	project_id=api_key,
	base_url=ApiUrls.mainnet.value,
)

try:
    health = api.health()
    print(health)   # prints object:    HealthResponse(is_healthy=True)
    health = api.health(return_type='json') # Can be useful if python wrapper is behind api version
    print(health)   # prints json:      {"is_healthy":True}
    health = api.health(return_type='pandas')
    print(health)   # prints Dataframe:         is_healthy
                    #                       0         True
except ApiError as e:
    print(e)


# Get our github api key from the file .env
# Then check login to github

personal_access_token = os.getenv('WAEL_PERSONAL_TOKEN')
# using an access token
g = Github(personal_access_token)

# Check that we can access the github api and returns correct user
try:   
    user = g.get_user()
    print(user.name)
except ApiError as e:
    print(e)


# Let's get the armada-alliance repo
repo = g.get_repo('armada-alliance/armada-alliance')

# Get contents of a file in the repo
contents = repo.get_contents("/services/website/content/en/stake-pools")
stake_pools = [x.name for x in contents]
stake_pools_no_extensions = [x.replace('.md', '') for x in stake_pools]

# Use the blockfrost api to get the stake pools data

def get_stake_pool_data(hex_pool_id):
        
        if len(hex_pool_id) == 0:
                return "Please enter a non empty list of hex pool ids"
        pool_data_df = pd.DataFrame()
        
        for i in hex_pool_id:
                try:
                        pool_data = api.pool(pool_id=i, return_type='pandas')
                        pool_data_df = pd.concat([pool_data_df,pool_data], axis=0, join='outer')
                
                except ApiError as e:
                        print(e)
                
        index = pd.Index(range(0,len(pool_data_df)))
        pool_data_df.set_index(index, inplace=True)
        return pool_data_df


pool_data_df = get_stake_pool_data(stake_pools_no_extensions)



# Create deadpools dataframe

def get_deadpools(pool_data_df):
        
        if len(pool_data_df) == 0:
                return "Please enter a non empty dataframe"
        
        deadpools_df = pd.DataFrame()
        
        for pool in range(len(pool_data_df)):

                if len(pool_data_df.retirement[pool]) > 0:
                        transposed_df = pd.DataFrame(pool_data_df.iloc[pool,:]).T
                        deadpools_df = pd.concat([deadpools_df, transposed_df], axis=0, join='outer')
                        print('Pool Id of retiring pools is: {}'.format(pool_data_df.pool_id[pool]))

        return deadpools_df


deadpools_df = get_deadpools(pool_data_df)



# Now we need to get the content from the github repo matching the hex ids

def get_deadpool_content_from_repo(deadpools_df, repo_contents_object):

        if len(deadpools_df) == 0:
                return "Please enter a non empty dataframe"
        
        deadpool_hex_ids = deadpools_df.hex.to_list()

        deadpools_content = pd.DataFrame()
        
        for i in repo_contents_object:
                pool_dict = {}
                if i.name.replace('.md', '') in deadpool_hex_ids:
                        pool_dict[i.name] = i.decoded_content
                        deadpools_content = pd.concat([deadpools_content, pd.Series(pool_dict)], axis=0, join='outer')
        return deadpools_content

if deadpools_df.empty==False:
        deadpools_content = get_deadpool_content_from_repo(deadpools_df, contents)
        deadpools_content.reset_index(inplace=True)
        deadpools_content.rename(columns={'index':'fileName', 0:'fileContent'}, inplace=True)
else:
        print('There are no deadpools')


# Upload the content to the new repo

def upload_content_to_repo(deadpools_content, new_repo_url):
        
        # Check for content
        if len(deadpools_content) == 0:
                return "Please enter a non empty list of content"
        
        # Create a new repo git object
        new_repo = g.get_repo(new_repo_url)
        
        for content in range(len(deadpools_content)):
                try:
                        new_repo.create_file(deadpools_content[content]['fileName'], 'Uploading deadpools', deadpools_content[content]['fileContent'])
                except ApiError as e:
                        print(e)
                        

def delete_old_pools(repo, contents, deadpools_df):
        for i in contents:
                if i.name.replace('.md', '') in deadpools_df.hex.to_list():
                        print(i.name)
                        repo.delete_file(i.path, "Deleting deadpools", i.sha)

if deadpools_df.empty==False:
        upload_content_to_repo(deadpools_content, 'armada-alliance/davey-jones-locker')
        # Delete the deadpool from the original repo if commit is successful
        delete_old_pools(repo, contents, deadpools_df)