import asyncio
import meraki.aio
import config
import pandas as pd
from tabulate import tabulate

# Instantiate async Meraki API client
aiomeraki = meraki.aio.AsyncDashboardAPI(
            config.api_key,
            base_url="https://api.meraki.com/api/v1",
            log_file_prefix=__file__[:-3],
            print_console=True,
            maximum_retries=config.max_retries,
            maximum_concurrent_requests=config.max_requests,
)

async def gather_clients(aiomeraki, net):
    clients = await aiomeraki.networks.getNetworkClients(net['id'], total_pages=-1)
    if clients !=[]:
        for client in clients:
            client['networkId']=net['id']
            client['netName']=net['name']
    return clients

async def gather_policies(aiomeraki, client):
    policy = await aiomeraki.networks.getNetworkClientPolicy(networkId= client['networkId'], clientId=client['id'])
    client_policy = client
    client_policy['devicePolicy']=policy['devicePolicy']
    client_policy['groupPolicyId']=policy['groupPolicyId']
    return client_policy

def print_tabulate(df):
    print(tabulate(df, headers='keys', tablefmt='fancy_grid'))

async def gather_teleworker_devices(aiomeraki):
    org_networks = await aiomeraki.organizations.getOrganizationNetworks(
        organizationId=config.org_id,
        total_pages=-1
    )
    get_tasks = []
    for network in org_networks:
        if 'appliance' in network['productTypes']:
            get_tasks.append(gather_clients(aiomeraki, network))
    results = []
    for task in asyncio.as_completed(get_tasks):
        result = await task
        for item in result:
            results.append(item)

    results_pd = pd.DataFrame(results)
    results_pd.to_csv('./clients_report.csv')

    policy_tasks = []
    for result in results:
        policy_tasks.append(gather_policies(aiomeraki=aiomeraki, client=result))

    policy_results = []
    for policy_task in asyncio.as_completed(policy_tasks):
        policy_result = await policy_task
        policy_results.append(policy_result)
    policy_results_pd = pd.DataFrame(policy_results)
    policy_results_pd.to_csv('./client_policy_report.csv')

    return results_pd, policy_results_pd

async def main(aiomeraki):
    async with aiomeraki:
        clients_pd, policies_pd = await gather_teleworker_devices(aiomeraki)

    return clients_pd, policies_pd

if __name__ == "__main__":
    # -------------------Gather teleworker specific data-------------------
    loop = asyncio.get_event_loop()
    clients_pd, policies_pd = loop.run_until_complete(main(aiomeraki))
