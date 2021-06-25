file=open()
record=open()
try
    flag=','
    while True:
        for s in file.readline().split() as line:
            if flag in s:
                for i in range(0,line.index(flag)-1):
                    cas+=line[0::line.index(i)]
                    cas+=' '
                cas+=','
                cas+=' '+line[line.index(i)::-1]

