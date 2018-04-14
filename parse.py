import config
import gspread, re, operator, os, errno, random
from wordcloud import WordCloud
from oauth2client.service_account import ServiceAccountCredentials

def main():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
    gc = gspread.authorize(credentials)
    sh = gc.open_by_key(config.SHEET)

    wsSent = sh.worksheet("Sent").get_all_values()
    wsRec = sh.worksheet("Received").get_all_values()
    sentHeaders = [x.lower() for x in wsSent[0]]
    recHeaders = [x.lower() for x in wsRec[0]]

    sent = [dict(zip(sentHeaders, wsSent[row])) for row in range (1, len(wsSent))]
    rec = [dict(zip(recHeaders, wsRec[row])) for row in range (1, len(wsRec))]

    conversations = getConversations(sent, rec)

    for number in conversations:
        if len(conversations[number]['sent']) + len(conversations[number]['received']) > config.MIN_TEXTS_TO_PROCESS:
            name = "'%s' (%s)" % (conversations[number]['name'], number) if conversations[number]['name'] != "" else "'%s'" % (number)
            print(name)
            processConversation(conversations[number])

def getConversations(sent, rec):
    ret = {}

    for text in sent:
        if len(text['number']) is 11 and text['number'][:1] == "1":
            text['number'] = text['number'][1:]

        if len(text['number']) is not 10:
            continue

        if text['number'] not in ret:
            ret[text['number']] = {
                'sent': [],
                'received': [],
                'name': '',
                'number': text['number'],
            }

        ret[text['number']]['sent'].append(text)
        ret[text['number']]['name'] = text['name']

    for text in rec:
        if len(text['number']) is 11 and text['number'][:1] == "1":
            text['number'] = text['number'][1:]

        if len(text['number']) is not 10:
            continue

        if text['number'] not in ret:
            ret[text['number']] = {
                'sent': [],
                'received': [],
                'name': '',
                'number': text['number'],
            }

        ret[text['number']]['received'].append(text)
        ret[text['number']]['name'] = text['name']

    return ret

def processConversation(conversation):
    dir = "%s/%s" % (config.OUTPUT_FOLDER, conversation['name'] if conversation['name'] != '' else conversation['number'])

    # write counts to files
    print("\tCounting words...")
    sent, received, total = countWords(conversation)

    if config.OUTPUT_COUNT_TXT:
        print("\tGenerating count txt...")
        writeKeyValuePairsToFile(sent, "%s/sent.txt" % (dir))
        writeKeyValuePairsToFile(received, "%s/received.txt" % (dir))
        writeKeyValuePairsToFile(total, "%s/total.txt" % (dir))

    if config.OUTPUT_WORDCLOUD:
        print("\tGenerating wordclouds...")
        generateWordCloud(sent, "%s/sent.jpg" % (dir))
        generateWordCloud(received, "%s/received.jpg" % (dir))
        generateWordCloud(total, "%s/total.jpg" % (dir))

def countWords(conversation):
    allWords = {}
    for sent in conversation['sent']:
        words = sent['text'].split()
        for word in words:
            word = re.sub("[^a-zA-Z]+", "", word).lower()
            if len(word) < config.MIN_WORD_LENGTH or word in config.IGNORED_WORDS or word[:4] == "http":
                continue

            if word not in allWords:
                allWords[word] = {
                    'sent': 0,
                    'received': 0,
                    'total': 0,
                }

            allWords[word]['sent'] += 1
            allWords[word]['total'] += 1

    for rec in conversation['received']:
        words = rec['text'].split()
        for word in words:
            word = re.sub("[^a-zA-Z]+", "", word).lower()
            if len(word) < config.MIN_WORD_LENGTH or word in config.IGNORED_WORDS or word[:4] == "http":
                continue

            if word not in allWords:
                allWords[word] = {
                    'sent': 0,
                    'received': 0,
                    'total': 0,
                }

            allWords[word]['received'] += 1
            allWords[word]['total'] += 1

    sent = extractSortedKeyFromDict('sent', allWords)
    received = extractSortedKeyFromDict('received', allWords)
    total = extractSortedKeyFromDict('total', allWords)

    return sent, received, total

def generateWordCloud(list, file):
    textList = []
    for word in list:
        textList += [word[0]] * word[1]
    random.shuffle(textList)

    wordcloud = WordCloud(
        width=config.WC_WIDTH,
        height=config.WC_HEIGHT,
        background_color=config.WC_BGCOLOR
    )
    wordcloud.generate(' '.join(textList))
    wordcloud.to_file(file)

def writeKeyValuePairsToFile(list, file):
    if not os.path.exists(os.path.dirname(file)):
        try:
            os.makedirs(os.path.dirname(file))
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                raise

    with open(file, "w") as f:
        for word in list:
            f.write("%s: %s\n" % (str(word[0]), str(word[1])))

def extractSortedKeyFromDict(key, dictionary):
    extract = {}
    for k in dictionary:
        if dictionary[k][key] > 0:
            extract[k] = dictionary[k][key]

    return sorted(extract.items(), key=lambda x:x[1], reverse=True)

if __name__ == "__main__":
	main()
