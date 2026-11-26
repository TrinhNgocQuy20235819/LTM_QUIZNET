CC = gcc
CFLAGS = -Wall -Wextra -std=c11 -O2 -D_POSIX_C_SOURCE=200809L -Iinclude -Ilib
LDFLAGS = -lpthread -lsqlite3

SRC_FILES = $(wildcard src/*.c) $(wildcard lib/*.c)
OBJ_FILES = $(patsubst %.c, build/%.o, $(notdir $(SRC_FILES)))
TARGET = quiznet_server

VPATH = src:lib

all: $(TARGET)

$(TARGET): $(OBJ_FILES)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

build/%.o: %.c | build
	$(CC) $(CFLAGS) -c $< -o $@

build:
	mkdir -p build

clean:
	rm -rf build $(TARGET)