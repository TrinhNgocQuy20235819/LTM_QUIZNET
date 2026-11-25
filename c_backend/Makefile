CC = gcc
CFLAGS = -Wall -Wextra -std=c11 -O2 -D_POSIX_C_SOURCE=200809L
LDFLAGS = -lpthread -lsqlite3

SRCS = server_core.c stream_io.c auth_question.c cJSON.c
OBJS = $(SRCS:.c=.o)
TARGET = quiznet_server

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(OBJS) $(TARGET)
