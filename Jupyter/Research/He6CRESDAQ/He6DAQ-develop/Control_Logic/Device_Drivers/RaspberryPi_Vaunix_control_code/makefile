all : test LMShid.o

# How we create LMShid.o
LMShid.o : LMShid.c LMShid.h
	gcc -o LMShid.o -c LMShid.c

# The final output is one or more linked object files
test : test.c LMShid.o LMShid.h
#	gcc -o test -lm -lpthread -lusb test.c LMShid.o /usr/lib/libhid.a
	gcc -o test -lm -lpthread -lusb test.c LMShid.o

# The final output is one or more linked object files
test2 : test2.c #LMShid.o LMShid.h
#	gcc -o test -lm -lpthread -lusbl test.c LMShid.o
	gcc -o test2 -lm test2.c -I.

clean :
	rm -f LMShid.o
	rm -f test
	rm -f test2

