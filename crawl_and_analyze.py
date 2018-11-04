import html2text
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
import urllib
from requests import get
import re
import os

politics = ['SFAS', 'SOP', 'FIN', 'EITF', 'SAB', 'FAS', 'GASB']

def check_if_contains_number(word):
	num = ['1','2','3','4','5','6','7','8','9','0']
	for character in word:
		if character in num:
			return True
			break
	return False

def extract_target_lines(): #return search_df, it contains those lines which need to be deeply searched
	raw_df = pd.read_excel('MAC.xlsx', sheetname = 0, header = 0, index_col = False, keep_default_na=True)
	col_names = ['LPERMNO', 'FYEAR', 'GVKEY', 'DATADATE', 'CONML', 'CIK', 'ACCHG', 'SFAS']
	search_df = pd.DataFrame(columns = col_names)
	for index, rows in raw_df.iterrows():
		if (pd.isnull(rows['SFAS']) == True) and (pd.isnull(rows['CIK']) == False):
			search_df = search_df.append({
				'LPERMNO': rows['LPERMNO'],
				'FYEAR': rows['FYEAR'],
				'GVKEY': rows['GVKEY'],
				'DATADATE': rows['DATADATE'],
				'CONML': rows['CONML'],
				'CIK': rows['CIK'],
				'ACCHG': rows['ACCHG'],
				'SFAS': ""
				}, ignore_index = True)
	return search_df

def prepare_CIK_ACCHG_DATADATE(search_df): #return a list of Tuples, each Tuple contains the CIK, ACCHG DATADATE
	prepared = []
	for index, row in search_df.iterrows():
		raw1_CIK = str(row['CIK'])
		length = len(raw1_CIK)
		raw2_CIK = raw1_CIK[:length-2]
		CIK = ''
		difference = 10 - len(raw2_CIK)
		for i in range(difference):
			CIK += '0'
		CIK += raw2_CIK
		ACCHG = str(row['ACCHG'])
		DATADATE = str(row['DATADATE'])[:10]
		Tuple = (CIK, ACCHG, DATADATE)
		prepared.append(Tuple)
	return prepared

def get_the_document(Tuple):#return the link of pool of the target document for 1 Tuple (CIK, ACCHG, DATADATE)
	common_url_front = 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK='
	common_url_back = '&type=10-k&dateb=&owner=exclude&count=40'
	CIK = Tuple[0]
	DATADATE = Tuple[2]
	filing_date = DATADATE.replace('-','')
	search_url = common_url_front + str(CIK) + common_url_back
	response = get(search_url)
	html_soup_all = BeautifulSoup(response.text, 'html.parser')
	line_container = html_soup_all.find_all('tr')
	date_and_doc = []
	for i in range(len(line_container)):
		try:
			html_soup_line = BeautifulSoup(str(line_container[i]), 'html.parser')
			date = re.search('\D\d{4}\D\d{2}\D\d{2}\D',str(line_container[i]))[0]
			date = date.replace('-','')
			date = date.replace('>', '')
			date = date.replace('<', '')
			document_link_container = html_soup_line.find_all('a', id="documentsbutton")
			doc_link = document_link_container[0]['href']
			date_doc_tuple = (date, doc_link)
			date_and_doc.append(date_doc_tuple)
		except:
			pass
	document_url = 'https://www.sec.gov'
	for i in range(len(date_and_doc)):
		if i != 0:
			if (filing_date < date_and_doc[i-1][0]) and (filing_date > date_and_doc[i][0]):
				document_url += date_and_doc[i-1][1]
	return document_url

def fix_the_document(document_url):
	response = get(document_url)
	soup1 = BeautifulSoup(response.text, 'html.parser')
	container = soup1.find_all('table', class_="tableFile")
	link_list = []
	for i in range(len(container)):
		soup2 = BeautifulSoup(str(container[i]), 'html.parser')
		container2 = soup2.find_all('a')
		for j in range(len(container2)):
			link_list.append(container2[j]['href'])
	real_document_url = 'https://www.sec.gov' + link_list[0]
	return real_document_url

def put_web_page_into_txt_file(real_document_url):
	response = get(real_document_url)
	soup = BeautifulSoup(response.text, 'html.parser')
	with open('report.txt','w') as f:
		raw1 = soup.get_text().replace('\n','')
		raw2 = re.sub("\s\s+" , " ", raw1)
		f.write(raw2)
	f.close()

def text_file_to_list(filename): #return a list of the words in the whole web page
	string = ''
	with open(filename,'r') as f:
		for line in f:
			string += line
	f.close()
	words = string.split(' ')
	return words

def position_of_two_words(words): #return a dictionary, keys are "adopt" and "accumulate", value is a list storing the positions of keys
	key1 = 'adopt'
	key2 = 'cumulat'
	list1 = []
	list2 = []
	for i in range (len(words)):
		if key1 in words[i].lower():
			list1.append(i)
		elif key2 in words[i].lower():
			list2.append(i)
	position = {key1: list1, key2: list2}
	return position

def possible_pairs(position):
	list1 = position['adopt']
	list2 = position['cumulat']
	pair_list = []
	for i in range(len(list1)):
		for j in range(len(list2)):
			if abs(list1[i]-list2[j]) <= 50:
				pair_list.append((list1[i],list2[j]))
	return pair_list

def get_possible_SFAS(pair_list, words, position, possible_range):
	possible_SFAS = []
	specific = []
	for pair in pair_list:
		for items in politics:
			if pair[0] < pair[1]:
				narrow_start = pair[0]
				narrow_end = pair[1]
				start = pair[0]-possible_range
				end = pair[1]+possible_range
				counter = 0
				for i, word in enumerate(words[narrow_start:narrow_end]):
					if counter == 0 and (items in word) and (items not in possible_SFAS) and (check_if_contains_number(words[start:end][i])==True or check_if_contains_number(words[start:end][i+1])==True):
						counter += 1
						possible_SFAS.append(items)
						specific.append(items + ' ' + words[start:end][i] + words[start:end][i+1] + ' pos = ' + str(start+i))
				if counter == 0:
					for i, word in enumerate(words[start:end]):
						if counter == 0 and (items in word) and (items not in possible_SFAS) and (check_if_contains_number(words[start:end][i])==True or check_if_contains_number(words[start:end][i+1])==True):
							counter += 1
							possible_SFAS.append(items)
							specific.append(items + ' ' + words[start:end][i] + words[start:end][i+1] + ' pos = ' + str(start+i))
			else:
				narrow_start = pair[1]
				narrow_end = pair[0]
				start = pair[1]-possible_range
				end = pair[0]+possible_range
				counter = 0
				for i, word in enumerate(words[narrow_start:narrow_end]):
					if counter == 0 and (items in word) and (items not in possible_SFAS) and (check_if_contains_number(words[start:end][i])==True or check_if_contains_number(words[start:end][i+1])==True):
						counter += 1
						possible_SFAS.append(items)
						specific.append(items + ' ' + words[start:end][i] + words[start:end][i+1] + ' pos = ' + str(start+i))
				if counter == 0:
					for i, word in enumerate(words[start:end]):
						if counter == 0 and (items in word) and (items not in possible_SFAS) and (check_if_contains_number(words[start:end][i])==True or check_if_contains_number(words[start:end][i+1])==True):
							counter += 1
							possible_SFAS.append(items)
							specific.append(items + ' ' + words[start:end][i] + words[start:end][i+1] + ' pos = ' + str(start+i))
	return specific

search_df = extract_target_lines()
prepared = prepare_CIK_ACCHG_DATADATE(search_df)
print(prepared)

for i, Tuple in enumerate(prepared):
	try:
		print(i)
		document_url = get_the_document(Tuple)
		real_document_url = fix_the_document(document_url)
		put_web_page_into_txt_file(real_document_url)
		words = text_file_to_list('report.txt')
		position = position_of_two_words(words)
		pair_list = possible_pairs(position)
		possible_range = 50
		specific = get_possible_SFAS(pair_list, words, position, possible_range)
		if len(specific) != 0:
			specific_string = ''
			for rules in specific:
				specific_string += rules
				specific_string += '; '
			with open ('result.txt', 'a') as f:
				f.write(Tuple[0]+'|||' + Tuple[2] + '|||' +specific_string+'; '+real_document_url+'\n')
			f.close()
			print('completed '+str(i))
		else:
			print("No policy found!")
		os.remove('report.txt')
	except:
		pass
