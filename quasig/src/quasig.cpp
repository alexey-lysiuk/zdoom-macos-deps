
#include <stdint.h>
#include <stdlib.h>

#include <pthread.h>
#include <unistd.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <mach/mach_time.h>


extern "C"
{

void* g_malloc(size_t size)
{
	return malloc(size);
}

void g_free(void* ptr)
{
	free(ptr);
}


struct GError
{
	uint32_t domain;
	int	code;
	char* message;
};

void g_clear_error(GError** err)
{
	if (nullptr != err && nullptr != *err)
	{
		free(*err);
		*err = nullptr;
	}
}


void g_return_if_fail_warning(const char* domain, const char* function, const char* expression)
{
}


enum GFileTest
{
  G_FILE_TEST_IS_REGULAR    = 1 << 0,
  G_FILE_TEST_IS_SYMLINK    = 1 << 1,
  G_FILE_TEST_IS_DIR        = 1 << 2,
  G_FILE_TEST_IS_EXECUTABLE = 1 << 3,
  G_FILE_TEST_EXISTS        = 1 << 4
};

int g_file_test(const char* filename, int test)
{
	if (filename == nullptr)
	{
		return 0;
	}

	if ((test & G_FILE_TEST_EXISTS) && (access(filename, F_OK) == 0))
	{
		return 1;
	}

	if ((test & G_FILE_TEST_IS_EXECUTABLE) && (access(filename, X_OK) == 0))
	{
		if (getuid() != 0)
		{
			return 1;
		}
	}
	else
	{
		test &= ~G_FILE_TEST_IS_EXECUTABLE;
	}

	if (test & G_FILE_TEST_IS_SYMLINK)
	{
		struct stat s;

		if ((lstat(filename, &s) == 0) && S_ISLNK(s.st_mode))
		{
			return 1;
		}
	}

	if (test & (G_FILE_TEST_IS_REGULAR | G_FILE_TEST_IS_DIR | G_FILE_TEST_IS_EXECUTABLE))
	{
		struct stat s;

		if (stat(filename, &s) == 0)
		{
			if ((test & G_FILE_TEST_IS_REGULAR) && S_ISREG(s.st_mode))
			{
				return 1;
			}

			if ((test & G_FILE_TEST_IS_DIR) && S_ISDIR(s.st_mode))
			{
				return 1;
			}

			if ((test & G_FILE_TEST_IS_EXECUTABLE) && ((s.st_mode & S_IXOTH) || (s.st_mode & S_IXUSR) || (s.st_mode & S_IXGRP)))
			{
				return 1;
			}
		}
	}

	return 0;
}


void g_strfreev(char** str_array)
{
	if (str_array)
	{
		for (size_t i = 0; str_array[i] != nullptr; i++)
		{
			g_free(str_array[i]);
		}

		g_free(str_array);
    }
}


int g_shell_parse_argv(const char* command_line, int* argcp, char*** argvp, GError** error)
{
	// Not implemented
	return 0;
}


struct GTimeVal
{
	long tv_sec;
	long tv_usec;
};

void g_get_current_time(GTimeVal* result)
{
	struct timeval r;
	gettimeofday(&r, nullptr);

	result->tv_sec = r.tv_sec;
	result->tv_usec = r.tv_usec;
}

int64_t g_get_monotonic_time()
{
	static mach_timebase_info_data_t timebase_info;

	if (timebase_info.denom == 0)
	{
		mach_timebase_info(&timebase_info);

		if (timebase_info.numer % 1000 == 0)
		{
			timebase_info.numer /= 1000;
		}
		else
		{
			timebase_info.denom *= 1000;
		}

		if (timebase_info.denom % timebase_info.numer == 0)
		{
			timebase_info.denom /= timebase_info.numer;
			timebase_info.numer = 1;
		}
	}

	return mach_absolute_time() / timebase_info.denom;
}


void g_usleep(unsigned long microseconds)
{
	usleep(microseconds);
}


struct GMutex
{
	pthread_mutex_t* p;
};

static pthread_mutex_t* g_mutex_impl_new()
{
	pthread_mutexattr_t attr;
	pthread_mutexattr_init(&attr);

	pthread_mutex_t* mutex = new pthread_mutex_t;
	pthread_mutex_init(mutex, &attr);

	pthread_mutexattr_destroy(&attr);

	return mutex;
}

static void g_mutex_impl_free(pthread_mutex_t* mutex)
{
	pthread_mutex_destroy(mutex);
	delete mutex;
}

static pthread_mutex_t* g_mutex_get_impl(GMutex* mutex)
{
	pthread_mutex_t* impl = mutex->p;
	__sync_synchronize();

	if (nullptr == impl)
    {
		impl = g_mutex_impl_new();

		if (__sync_val_compare_and_swap(&mutex->p, nullptr, impl) != nullptr)
		{
			g_mutex_impl_free(impl);
			impl = mutex->p;
		}
	}

	return impl;
}

void g_mutex_init(GMutex* mutex)
{
	mutex->p = g_mutex_impl_new();
}

void g_mutex_clear(GMutex* mutex)
{
	g_mutex_impl_free(mutex->p);
}

void g_mutex_lock(GMutex* mutex)
{
	pthread_mutex_lock(g_mutex_get_impl(mutex));
}

void g_mutex_unlock(GMutex* mutex)
{
	pthread_mutex_unlock(g_mutex_get_impl(mutex));
}


struct GRecMutex
{
	pthread_mutex_t* p;
	unsigned int i[2];
};

static pthread_mutex_t* g_rec_mutex_impl_new()
{
	pthread_mutexattr_t attr;
	pthread_mutexattr_init(&attr);
	pthread_mutexattr_settype(&attr, PTHREAD_MUTEX_RECURSIVE);

	pthread_mutex_t* mutex = new pthread_mutex_t;
	pthread_mutex_init(mutex, &attr);

	pthread_mutexattr_destroy(&attr);

	return mutex;
}

static void g_rec_mutex_impl_free(pthread_mutex_t* mutex)
{
	pthread_mutex_destroy(mutex);
	delete mutex;
}

static pthread_mutex_t* g_rec_mutex_get_impl(GRecMutex* mutex)
{
	pthread_mutex_t* impl = mutex->p;
	__sync_synchronize();

	if (nullptr == impl)
    {
		impl = g_rec_mutex_impl_new();

		if (__sync_val_compare_and_swap(&mutex->p, nullptr, impl) != nullptr)
		{
			g_rec_mutex_impl_free(impl);
			impl = mutex->p;
		}
    }

	return impl;
}

void g_rec_mutex_init(GRecMutex* mutex)
{
	mutex->p = g_rec_mutex_impl_new();
}

void g_rec_mutex_clear(GRecMutex* mutex)
{
	g_rec_mutex_impl_free(mutex->p);
}

void g_rec_mutex_lock(GRecMutex* mutex)
{
	pthread_mutex_lock(g_rec_mutex_get_impl(mutex));
}

void g_rec_mutex_unlock(GRecMutex* mutex)
{
	pthread_mutex_unlock(g_rec_mutex_get_impl(mutex));
}


struct GCond
{
	pthread_cond_t* p;
	unsigned int i[2];
};

static pthread_cond_t* g_cond_impl_new()
{
	pthread_condattr_t attr;
	pthread_condattr_init(&attr);

	pthread_cond_t* cond = new pthread_cond_t;
	pthread_cond_init(cond, &attr);

	return cond;
}

static void g_cond_impl_free(pthread_cond_t* cond)
{
	pthread_cond_destroy(cond);
	delete cond;
}

static pthread_cond_t* g_cond_get_impl(GCond* cond)
{
	pthread_cond_t* impl = cond->p;
	__sync_synchronize();

	if (nullptr == impl)
	{
		impl = g_cond_impl_new();

		if (__sync_val_compare_and_swap(&cond->p, nullptr, impl) != nullptr)
		{
			g_cond_impl_free(impl);
			impl = cond->p;
		}
	}

	return impl;
}

void g_cond_init(GCond* cond)
{
	cond->p = g_cond_impl_new();
}

void g_cond_clear(GCond* cond)
{
	g_cond_impl_free(cond->p);
}

void g_cond_wait(GCond* cond, GMutex* mutex)
{
	pthread_cond_wait(g_cond_get_impl(cond), g_mutex_get_impl(mutex));
}

void g_cond_signal(GCond* cond)
{
	pthread_cond_signal(g_cond_get_impl(cond));
}

void g_cond_broadcast(GCond* cond)
{
	pthread_cond_broadcast(g_cond_get_impl(cond));
}


using GDestroyNotify = void (*)(void* data);

struct GPrivate
{
	pthread_key_t* p;
	GDestroyNotify notify;
	void* future[2];
};

static pthread_key_t* g_private_impl_new(GDestroyNotify notify)
{
	pthread_key_t* key = new pthread_key_t;
	pthread_key_create(key, notify);
	return key;
}

static void g_private_impl_free(pthread_key_t* key)
{
	pthread_key_delete(*key);
	delete key;
}

static inline pthread_key_t* g_private_get_impl(GPrivate* key)
{
	pthread_key_t* impl = key->p;
	__sync_synchronize();

	if (nullptr == impl)
    {
		impl = g_private_impl_new(key->notify);

		if (__sync_val_compare_and_swap(&key->p, nullptr, impl) != nullptr)
        {
			g_private_impl_free(impl);
			impl = key->p;
        }
    }

  return impl;
}

void* g_private_get(GPrivate* key)
{
	return pthread_getspecific(*g_private_get_impl(key));
}

void g_private_set(GPrivate* key, void* value)
{
	pthread_setspecific(*g_private_get_impl(key), value);
}


struct GThread
{
	pthread_t thread;
	int ref_count;
};

using GThreadFunc = void* (*)(void* data);

GThread* g_thread_try_new(const char* name, GThreadFunc func, void* data, GError** error)
{
	if (error != nullptr)
	{
		*error = nullptr;
	}

	pthread_attr_t attr;
	pthread_attr_init(&attr);

	GThread* thread = new GThread;
	pthread_create(&thread->thread, &attr, func, data);
	thread->ref_count = 1;

	pthread_attr_destroy(&attr);

	return thread;
}

void* g_thread_join(GThread* thread)
{
	void* result = nullptr;
	pthread_join(thread->thread, &result);
	return result;
}

void g_thread_unref(GThread* thread)
{
	if (__sync_sub_and_fetch(&thread->ref_count, 1) == 0)
	{
		g_thread_join(thread);
		delete thread;
	}
}

}
