import requests
from bs4 import BeautifulSoup
import ipaddress
import os

isps_to_search = {
    "China Mobile": ["mobile", "tietong"],
    "China Unicom": ["cnc", "cncgroup", "unicom", "netcom"],
    "China Telecom": ["chinatelecom", "telecom", "chinanet", "ct"]
}

def clear_cache():
    for isp in isps_to_search.keys():
        for version in ['v4', 'v6']:
            filename = f"{isp.replace(' ', '_')}_{version}.txt"
            if os.path.exists(filename):
                os.remove(filename)
                print(f"清除缓存文件: {filename}")

def cache_asn_page(isp_keyword):
    search_url = f"https://bgp.he.net/search?search%5Bsearch%5D={isp_keyword}&commit=Search"
    print(f"缓存ASN页面: {search_url}")
    response = requests.get(search_url)
    return response.content

def get_unique_asns(isp_keywords):
    asns = {}
    for keyword in isp_keywords:
        page_content = cache_asn_page(keyword)
        soup = BeautifulSoup(page_content, 'html.parser')
        print(f"从关键词 '{keyword}' 获取ASN...")
        for row in soup.find_all('tr'):
            if 'ASN' in row.text:
                # 检查是否有标记为中国的图片
                if row.find('img') and row.find('img')['title'] == "China":
                    asn = row.find('a').text.strip()
                    name = row.find_all('td')[2].text.strip()  # 获取名称
                    asns[asn] = name  # 存储ASN和名称
                    print(f"发现 {asn}，名称 {name}")
    return asns

def get_cidr(asn):
    cidrs_v4 = []
    cidrs_v6 = []
    
    for suffix in ["#_prefixes", "#_prefixes6"]:
        asn_page = requests.get(f"https://bgp.he.net/{asn}{suffix}").content
        soup = BeautifulSoup(asn_page, 'html.parser')
        print(f"获取ASN {asn} 的CIDR信息...")
        for row in soup.find_all('tr'):
            cidr_link = row.find('a')
            if cidr_link and 'net' in cidr_link['href']:
                cidr = cidr_link.text.strip()
                try:
                    ipaddress.ip_network(cidr)  # 验证CIDR是否有效
                    if ':' in cidr:  # IPv6
                        cidrs_v6.append(cidr)
                    else:  # IPv4
                        cidrs_v4.append(cidr)
                except ValueError:
                    print(f"警告：跳过无效的CIDR: {cidr}")
    
    # 打印发现的CIDR数量
    total_cidrs = len(cidrs_v4) + len(cidrs_v6)
    print(f"ASN {asn} 发现 {total_cidrs} 个 CIDR (IPv4: {len(cidrs_v4)}, IPv6: {len(cidrs_v6)})")
    
    return cidrs_v4, cidrs_v6

def merge_and_sort_cidrs(cidrs):
    cidr_set = set()
    for cidr in cidrs:
        try:
            cidr_set.add(ipaddress.ip_network(cidr))
        except ValueError:
            print(f"警告：跳过无效的CIDR: {cidr}")
    print(f"开始合并 {len(cidr_set)} CIDR，原始数量: {len(cidrs)}")
    merged = list(ipaddress.collapse_addresses(cidr_set))  # 转换为列表
    print(f"CIDR合并完成，合并后数量: {len(merged)}")
    return sorted(str(cidr) for cidr in merged)

def main():
    clear_cache()

    for isp, keywords in isps_to_search.items():
        print(f"\n正在搜索ISP: {isp}")
        unique_asns = get_unique_asns(keywords)
        all_cidrs_v4 = []
        all_cidrs_v6 = []
        
        for asn, name in unique_asns.items():
            cidrs_v4, cidrs_v6 = get_cidr(asn)
            all_cidrs_v4.extend(cidrs_v4)
            all_cidrs_v6.extend(cidrs_v6)
        
        # 在所有CIDR提取完成后再合并
        merged_cidrs_v4 = merge_and_sort_cidrs(all_cidrs_v4)
        merged_cidrs_v6 = merge_and_sort_cidrs(all_cidrs_v6)

        with open(f"{isp.replace(' ', '_')}_v4.txt", 'w') as f_v4:
            for cidr in merged_cidrs_v4:
                f_v4.write(cidr + '\n')

        with open(f"{isp.replace(' ', '_')}_v6.txt", 'w') as f_v6:
            for cidr in merged_cidrs_v6:
                f_v6.write(cidr + '\n')

if __name__ == "__main__":
    main()
