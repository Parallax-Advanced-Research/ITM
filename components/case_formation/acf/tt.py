def generateDiff(df_top5_train, df_test):
    output1 = ''
    # first sample
    if (df_top5_train.iloc[0]['type'] != df_test.iloc[0]['type']):
        if output1 == '':
            output1 += "Type: "+str(df_top5_train.iloc[0]['type'])+"/"+str(df_test.iloc[0]['type'])
        else:
            output1 += ", Type: " + str(df_top5_train.iloc[0]['type']) + "/" + str(df_test.iloc[0]['type'])
    if (df_top5_train.iloc[0]['mission'] != df_test.iloc[0]['mission']):
        if output1 == '':
            output1 += "Mission: "+str(df_top5_train.iloc[0]['mission'])+"/"+str(df_test.iloc[0]['mission'])
        else:
            output1 += ", Mission: " + str(df_top5_train.iloc[0]['mission']) + "/" + str(df_test.iloc[0]['mission'])
    if (df_top5_train.iloc[0]['denial'] != df_test.iloc[0]['denial']):
        if output1 == '':
            output1 += "Denial: "+str(df_top5_train.iloc[0]['denial'])+"/"+str(df_test.iloc[0]['denial'])
        else:
            output1 += ", Denial: " + str(df_top5_train.iloc[0]['denial']) + "/" + str(df_test.iloc[0]['denial'])
    if (df_top5_train.iloc[0]['risktol'] != df_test.iloc[0]['risktol']):
        if output1 == '':
            output1 += "Risktol: "+str(df_top5_train.iloc[0]['risktol'])+"/"+str(df_test.iloc[0]['risktol'])
        else:
            output1 += ", Risktol: " + str(df_top5_train.iloc[0]['risktol']) + "/" + str(df_test.iloc[0]['risktol'])
    if (df_top5_train.iloc[0]['timeurg'] != df_test.iloc[0]['timeurg']):
        if output1 == '':
            output1 += "Timeurg: "+str(df_top5_train.iloc[0]['timeurg'])+"/"+str(df_test.iloc[0]['timeurg'])
        else:
            output1 += ", Timeurg: " + str(df_top5_train.iloc[0]['timeurg']) + "/" + str(df_test.iloc[0]['timeurg'])

    # second sample
    output2 = ''
    if (df_top5_train.iloc[1]['type'] != df_test.iloc[0]['type']):
        if output2 == '':
            output2 += "Type: " + str(df_top5_train.iloc[1]['type']) + "/" + str(df_test.iloc[0]['type'])
        else:
            output2 += ", Type: " + str(df_top5_train.iloc[1]['type']) + "/" + str(df_test.iloc[0]['type'])
    if (df_top5_train.iloc[1]['mission'] != df_test.iloc[0]['mission']):
        if output2 == '':
            output2 += "Mission: " + str(df_top5_train.iloc[1]['mission']) + "/" + str(df_test.iloc[0]['mission'])
        else:
            output2 += ", Mission: " + str(df_top5_train.iloc[1]['mission']) + "/" + str(df_test.iloc[0]['mission'])
    if (df_top5_train.iloc[1]['denial'] != df_test.iloc[0]['denial']):
        if output2 == '':
            output2 += "Denial: " + str(df_top5_train.iloc[1]['denial']) + "/" + str(df_test.iloc[0]['denial'])
        else:
            output2 += ", Denial: " + str(df_top5_train.iloc[1]['denial']) + "/" + str(df_test.iloc[0]['denial'])
    if (df_top5_train.iloc[1]['risktol'] != df_test.iloc[0]['risktol']):
        if output2 == '':
            output2 += "Risktol: " + str(df_top5_train.iloc[1]['risktol']) + "/" + str(df_test.iloc[0]['risktol'])
        else:
            output2 += ", Risktol: " + str(df_top5_train.iloc[1]['risktol']) + "/" + str(df_test.iloc[0]['risktol'])
    if (df_top5_train.iloc[1]['timeurg'] != df_test.iloc[0]['timeurg']):
        if output2 == '':
            output2 += "Timeurg: "+str(df_top5_train.iloc[1]['timeurg'])+"/"+str(df_test.iloc[0]['timeurg'])
        else:
            output2 += ", Timeurg: " + str(df_top5_train.iloc[1]['timeurg']) + "/" + str(df_test.iloc[0]['timeurg'])
    # third sample
    output3 = ''
    if (df_top5_train.iloc[2]['type'] != df_test.iloc[0]['type']):
        if output3 == '':
            output3 += "Type: " + str(df_top5_train.iloc[2]['type']) + "/" + str(df_test.iloc[0]['type'])
        else:
            output3 += ", Type: " + str(df_top5_train.iloc[2]['type']) + "/" + str(df_test.iloc[0]['type'])
    if (df_top5_train.iloc[2]['mission'] != df_test.iloc[0]['mission']):
        if output3 == '':
            output3 += "Mission: " + str(df_top5_train.iloc[2]['mission']) + "/" + str(df_test.iloc[0]['mission'])
        else:
            output3 += ", Mission: " + str(df_top5_train.iloc[2]['mission']) + "/" + str(df_test.iloc[0]['mission'])
    if (df_top5_train.iloc[2]['denial'] != df_test.iloc[0]['denial']):
        if output3 == '':
            output3 += "Denial: " + str(df_top5_train.iloc[2]['denial']) + "/" + str(df_test.iloc[0]['denial'])
        else:
            output3 += ", Denial: " + str(df_top5_train.iloc[2]['denial']) + "/" + str(df_test.iloc[0]['denial'])
    if (df_top5_train.iloc[2]['risktol'] != df_test.iloc[0]['risktol']):
        if output3 == '':
            output3 += "Risktol: " + str(df_top5_train.iloc[2]['risktol']) + "/" + str(df_test.iloc[0]['risktol'])
        else:
            output3 += ", Risktol: " + str(df_top5_train.iloc[2]['risktol']) + "/" + str(df_test.iloc[0]['risktol'])
    if (df_top5_train.iloc[2]['timeurg'] != df_test.iloc[0]['timeurg']):
        if output3 == '':
            output3 += "Timeurg: " + str(df_top5_train.iloc[2]['timeurg']) + "/" + str(df_test.iloc[0]['timeurg'])
        else:
            output3 += ", Timeurg: " + str(df_top5_train.iloc[2]['timeurg']) + "/" + str(df_test.iloc[0]['timeurg'])
    # fourth sample
    output4 = ''
    if (df_top5_train.iloc[3]['type'] != df_test.iloc[0]['type']):
        if output4 == '':
            output4 += "Type: " + str(df_top5_train.iloc[3]['type']) + "/" + str(df_test.iloc[0]['type'])
        else:
            output4 += ", Type: " + str(df_top5_train.iloc[3]['type']) + "/" + str(df_test.iloc[0]['type'])
    if (df_top5_train.iloc[3]['mission'] != df_test.iloc[0]['mission']):
        if output4 == '':
            output4 += "Mission: " + str(df_top5_train.iloc[3]['mission']) + "/" + str(df_test.iloc[0]['mission'])
        else:
            output4 += ", Mission: " + str(df_top5_train.iloc[3]['mission']) + "/" + str(df_test.iloc[0]['mission'])
    if (df_top5_train.iloc[3]['denial'] != df_test.iloc[0]['denial']):
        if output4 == '':
            output4 += "Denial: " + str(df_top5_train.iloc[3]['denial']) + "/" + str(df_test.iloc[0]['denial'])
        else:
            output4 += ", Denial: " + str(df_top5_train.iloc[3]['denial']) + "/" + str(df_test.iloc[0]['denial'])
    if (df_top5_train.iloc[3]['risktol'] != df_test.iloc[0]['risktol']):
        if output4 == '':
            output4 += "Risktol: " + str(df_top5_train.iloc[3]['risktol']) + "/" + str(df_test.iloc[0]['risktol'])
        else:
            output4 += ", Risktol: " + str(df_top5_train.iloc[3]['risktol']) + "/" + str(df_test.iloc[0]['risktol'])
    if (df_top5_train.iloc[3]['timeurg'] != df_test.iloc[0]['timeurg']):
        if output4 == '':
            output4 += "Timeurg: " + str(df_top5_train.iloc[3]['timeurg']) + "/" + str(df_test.iloc[0]['timeurg'])
        else:
            output4 += ", Timeurg: " + str(df_top5_train.iloc[3]['timeurg']) + "/" + str(df_test.iloc[0]['timeurg'])
    # fifth sample
    output5 = ''
    if (df_top5_train.iloc[4]['type'] != df_test.iloc[0]['type']):
        if output5 == '':
            output5 += "Type: " + str(df_top5_train.iloc[4]['type']) + "/" + str(df_test.iloc[0]['type'])
        else:
            output5 += ", Type: " + str(df_top5_train.iloc[4]['type']) + "/" + str(df_test.iloc[0]['type'])
    if (df_top5_train.iloc[4]['mission'] != df_test.iloc[0]['mission']):
        if output5 == '':
            output5 += "Mission: " + str(df_top5_train.iloc[4]['mission']) + "/" + str(df_test.iloc[0]['mission'])
        else:
            output5 += ", Mission: " + str(df_top5_train.iloc[4]['mission']) + "/" + str(df_test.iloc[0]['mission'])
    if (df_top5_train.iloc[4]['denial'] != df_test.iloc[0]['denial']):
        if output5 == '':
            output5 += "Denial: " + str(df_top5_train.iloc[4]['denial']) + "/" + str(df_test.iloc[0]['denial'])
        else:
            output5 += ", Denial: " + str(df_top5_train.iloc[4]['denial']) + "/" + str(df_test.iloc[0]['denial'])
    if (df_top5_train.iloc[4]['risktol'] != df_test.iloc[0]['risktol']):
        if output5 == '':
            output5 += "Risktol: " + str(df_top5_train.iloc[4]['risktol']) + "/" + str(df_test.iloc[0]['risktol'])
        else:
            output5 += ", Risktol: " + str(df_top5_train.iloc[4]['risktol']) + "/" + str(df_test.iloc[0]['risktol'])
    if (df_top5_train.iloc[4]['timeurg'] != df_test.iloc[0]['timeurg']):
        if output5 == '':
            output5 += "Timeurg: " + str(df_top5_train.iloc[4]['timeurg']) + "/" + str(df_test.iloc[0]['timeurg'])
        else:
            output5 += ", Timeurg: " + str(df_top5_train.iloc[4]['risktol']) + "/" + str(df_test.iloc[0]['timeurg'])
    return output1, output2, output3, output4, output5