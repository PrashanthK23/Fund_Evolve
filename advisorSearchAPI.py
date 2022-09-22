import json

from flask import Flask, request, jsonify

from config import properties
import pandas as pd
import numpy as np
import collections
import requests

app = Flask(__name__)

class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NpEncoder, self).default(obj)

def getAdvisors():
    response = requests.get("https://fundevolve02.herokuapp.com/api/advisors/list")
    response=pd.json_normalize(response.json())
    response=response.explode('languages')
    response=response.explode('specializations')
    return response

def getclientChoice(client, each_column):
    if each_column=='languages':
        clientList= list(each_lan['value'] for each_lan in client['formData']['languages'])
    elif each_column=='gender':
        clientList= [client['formData']['identity']]
    elif each_column=='specializations':
        clientList= list(each_lan['value'] for each_lan in client['formData']['areaOfSpecialties'])
    return clientList

def filteredAdvisors(client, df_advisors):
    percentage = {}
    match_list = {}
    filter_columns = properties.filters
    print(client['formData'])
    print(client['formData']['identity'])
    if client['formData']['identity'] == 'D':
        filter_columns.remove('gender')
    for each_column in filter_columns:
        clientList = getclientChoice(client, each_column)
        filtered_Advisors = df_advisors[df_advisors[each_column].isin(clientList)]
        for each_advisor in filtered_Advisors.id.unique():
            advisor_list = list(filtered_Advisors[filtered_Advisors.id == each_advisor][each_column])
            if each_advisor in percentage:
                percentage[each_advisor] = percentage[each_advisor] + 20
                match_list[each_advisor] = match_list[each_advisor] + list(set(advisor_list) & set(clientList))
            else:
                percentage[each_advisor] = 20
                match_list[each_advisor] = list(set(advisor_list) & set(clientList))
    return filtered_Advisors, percentage, match_list

def get_client_list(each_pro, client):
    if each_pro == 'investmentSize':
        client_list = [client['formData']['totalInvestableAssets']]
        return client_list
    else:
        return None


def rankAdvisors(client, filtered_Advisors,percentage,match_list):
    advisor_score={}
    # if client['formData']['advisorAvailability']=='yes':
    #     cli_lat =43.731
    #     cli_lon =79.762
    #     for ind,each_advisor in filtered_Advisors[['advisorid','lat','lon']].drop_duplicates().iterrows():
    #         adv_lat=each_advisor.lat
    #         adv_lon=each_advisor.lat
    #         distance=np.sqrt(((adv_lat-cli_lat)**2)+((adv_lon-cli_lon)**2))
    #         advisorid=each_advisor.advisorid
    #         advisor_score[advisorid]=distance
    #     mean=sum(advisor_score.values()) / len(advisor_score)
    #     for each_key in advisor_score:
    #         advisor_score[each_key]=10-(advisor_score[each_key]/mean)
    #         if advisor_score[each_key]<5:
    #             if each_key in percentage:
    #                 percentage[each_key] = percentage[each_key] + 5
    #             else:
    #                 percentage[each_key] = 5
    #         else:
    #             if each_key in percentage:
    #                 percentage[each_key]=percentage[each_key]+15
    #                 match_list[each_key] = match_list[each_key]+['nearest place']
    #             else:
    #                 percentage[each_key] =15
    #                 match_list[each_key] = ['nearest place']
    for each_advisor in filtered_Advisors.id.unique():
        for each_pro in properties.weightage:
            advisor_list=list(filtered_Advisors[filtered_Advisors.id==each_advisor][each_pro])
            client_list=get_client_list(each_pro,client)
            similar_count=len(set(advisor_list)&set(client_list))
            if each_advisor in advisor_score:
                advisor_score[each_advisor]=advisor_score[each_advisor]+(properties.weightage[each_pro]*similar_count)
            else:
                advisor_score[each_advisor]=properties.weightage[each_pro]*similar_count
            if similar_count>0:
                if each_advisor in percentage:
                    percentage[each_advisor] = percentage[each_advisor] + ((similar_count/len(client_list))*20)
                    match_list[each_advisor] = match_list[each_advisor]+list(set(advisor_list) & set(client_list))
                else:
                    percentage[each_advisor] = (similar_count/len(client_list))*20
                    match_list[each_advisor] = list(set(advisor_list) & set(client_list))

    return advisor_score,percentage,match_list



@app.route('/api/v1/searchadvisor', methods=['GET', 'POST'])
def search_advisor():
    print('start')
    df_clients = request.json
    df_advisors = getAdvisors()
    filtered_Advisors, percentage, match_list = filteredAdvisors(df_clients, df_advisors)
    print('after filtered_Advisors')
    advisor_score, percentage, match_list = rankAdvisors(df_clients, filtered_Advisors, percentage, match_list)
    print('after advisor_score')
    response = []
    for each_advisor in advisor_score:
        if each_advisor in percentage and each_advisor in match_list:
            response.append({'advisor':{'id':each_advisor,"firstName":df_advisors.firstName.iloc[0],"lastName":df_advisors.lastName.iloc[0],"gender":df_advisors.gender.iloc[0],'match_list':match_list[each_advisor],'advisor_score': advisor_score[each_advisor]},'percentage':percentage[each_advisor]})
        else:
            response.append({'advisor': {'id': each_advisor,"firstName":df_advisors.firstName.iloc[0],"lastName":df_advisors.lastName.iloc[0],"gender":df_advisors.gender.iloc[0],'match_list':[],'advisor_score': advisor_score[each_advisor]},
                             'percentage': 0})
    return json.dumps(response, cls=NpEncoder)


if __name__ == '__main__':
    print('in main')
    app.run()
    #search_advisor()
